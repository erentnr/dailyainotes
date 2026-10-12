from collections.abc import Callable

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from dailyainotes.domain.llm_usage import CallRecord, Usage
from dailyainotes.llm.router import (
    DailyLimit,
    ModelRef,
    ModelsExhaustedError,
    Router,
    extract_json,
    parse_chain,
)

pytestmark = pytest.mark.anyio

PRIMARY = ModelRef("ollama", "big:1b")
FALLBACK = ModelRef("openrouter", "small/model:free")


class Answer(BaseModel):
    value: int


class MemoryLedger:
    def __init__(self, usage: dict[str, Usage] | None = None) -> None:
        self.calls: list[CallRecord] = []
        self.usage = usage or {}

    async def record(self, run_id: int | None, call: CallRecord) -> None:
        self.calls.append(call)

    async def usage_today(self, provider: str) -> Usage:
        return self.usage.get(provider, Usage(0, 0))


class Broken(FakeListChatModel):
    """A model that fails like a rate-limited or unreachable provider."""

    async def ainvoke(self, *args: object, **kwargs: object) -> AIMessage:  # type: ignore[override]
        raise ConnectionError("429 Too Many Requests")


def models(**replies: list[str] | None) -> Callable[[ModelRef], BaseChatModel]:
    """`models(ollama=["{...}"], openrouter=None)`: None means the provider is down."""

    def make(ref: ModelRef) -> BaseChatModel:
        answers = replies[ref.provider]
        return Broken(responses=[""]) if answers is None else FakeListChatModel(responses=answers)

    return make


def router(ledger: MemoryLedger, **replies: list[str] | None) -> Router:
    return Router(
        {"planner": [PRIMARY, FALLBACK]},
        models(**replies),
        ledger,
        limits={"openrouter": DailyLimit(requests=50)},
    )


async def ask(r: Router) -> Answer:
    return await r.structured("planner", Answer, system="Add.", user="2+2")


async def test_the_first_model_answers_when_it_can() -> None:
    ledger = MemoryLedger()

    answer = await ask(router(ledger, ollama=['{"value": 4}'], openrouter=['{"value": 5}']))

    assert answer.value == 4
    assert [(c.provider, c.ok, c.fell_back) for c in ledger.calls] == [("ollama", True, False)]


async def test_a_failing_provider_falls_back_to_the_next() -> None:
    ledger = MemoryLedger()

    answer = await ask(router(ledger, ollama=None, openrouter=['{"value": 4}']))

    assert answer.value == 4
    assert [(c.provider, c.ok, c.fell_back) for c in ledger.calls] == [
        ("ollama", False, False),
        ("openrouter", True, True),
    ]


async def test_invalid_output_gets_one_repair_attempt() -> None:
    ledger = MemoryLedger()

    answer = await ask(router(ledger, ollama=["four", '```json\n{"value": 4}\n```'], openrouter=[]))

    assert answer.value == 4
    assert [(c.ok, c.error) for c in ledger.calls] == [(False, "invalid output"), (True, "")]


async def test_invalid_output_twice_moves_on_to_the_next_model() -> None:
    ledger = MemoryLedger()

    answer = await ask(router(ledger, ollama=["four", "still four"], openrouter=['{"value": 4}']))

    assert answer.value == 4
    assert ledger.calls[-1].provider == "openrouter"


async def test_a_provider_over_its_daily_limit_is_skipped() -> None:
    ledger = MemoryLedger({"openrouter": Usage(requests=50, tokens=0)})

    with pytest.raises(ModelsExhaustedError) as failure:
        await ask(router(ledger, ollama=None, openrouter=['{"value": 4}']))

    assert failure.value.attempts == [
        "ollama:big:1b: ConnectionError",
        "openrouter:small/model:free: daily budget used",
    ]


def test_a_chain_keeps_colons_inside_model_names() -> None:
    assert parse_chain("ollama:gpt-oss:120b, openrouter:google/gemma-4-31b-it:free") == [
        ModelRef("ollama", "gpt-oss:120b"),
        ModelRef("openrouter", "google/gemma-4-31b-it:free"),
    ]


@pytest.mark.parametrize("spec", ["", "ollama", "openai:gpt-6", "ollama:"])
def test_a_malformed_chain_is_rejected(spec: str) -> None:
    with pytest.raises(ValueError, match="provider:model"):
        parse_chain(spec)


@pytest.mark.parametrize(
    "reply",
    ['{"value": 4}', '```json\n{"value": 4}\n```', 'Sure! {"value": 4} Hope that helps.'],
)
def test_the_json_object_is_found_in_a_reply(reply: str) -> None:
    assert extract_json(reply) == '{"value": 4}'


def test_a_reply_without_json_is_an_error() -> None:
    with pytest.raises(ValueError, match="no JSON"):
        extract_json("four")
