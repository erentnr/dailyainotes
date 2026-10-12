"""The LLM router, the only way to call a model (INTENT.md, Architectural Constraints).

Each role has an ordered chain of `provider:model`. The router tries them in order and moves
on when a call fails (rate limit, exhausted quota, timeout, missing key) or when the answer
is not valid JSON for the schema after one repair attempt. Structured output is asked for in
the prompt and checked with Pydantic, which works on every provider, including Ollama's cloud,
whose docs say it has no native structured output.
"""

import asyncio
import json
import re
import time
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

import structlog
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ValidationError

from dailyainotes.domain.llm_usage import CallRecord, Usage

log = structlog.get_logger(__name__)

PROVIDERS = {"ollama", "openrouter"}
# Requests one provider may serve at once. Ollama's free plan allows one.
CONCURRENCY = {"ollama": 1}
FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


@dataclass(frozen=True)
class ModelRef:
    provider: str
    model: str

    def __str__(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass(frozen=True)
class DailyLimit:
    requests: int | None = None
    tokens: int | None = None

    def allows(self, usage: Usage) -> bool:
        over_requests = self.requests is not None and usage.requests >= self.requests
        over_tokens = self.tokens is not None and usage.tokens >= self.tokens
        return not (over_requests or over_tokens)


class Ledger(Protocol):
    async def record(self, run_id: int | None, call: CallRecord) -> None: ...

    async def usage_today(self, provider: str) -> Usage: ...


class ModelsExhaustedError(Exception):
    """Every model in a role's chain failed; `attempts` says how."""

    def __init__(self, role: str, attempts: list[str]) -> None:
        super().__init__(f"no model answered for {role}: {'; '.join(attempts)}")
        self.attempts = attempts


def describe(error: BaseException) -> str:
    """What failed, in one short line: the type, the status and the message's first line.
    Providers' errors carry the whole response, with cookies and the account's id; that stays
    out of the logs and the ledger."""
    status = getattr(error, "status_code", None)
    message = str(getattr(error, "message", None) or error)
    first_line = message.splitlines()[0] if message else ""
    text = type(error).__name__ + (f" {status}" if status else "")
    return (f"{text}: {first_line}" if first_line else text)[:300]


def parse_chain(spec: str) -> list[ModelRef]:
    """`"ollama:gpt-oss:120b,openrouter:a/b:free"` → two refs; the model keeps its colons."""
    refs = []
    for part in (p.strip() for p in spec.split(",")):
        provider, _, model = part.partition(":")
        if provider not in PROVIDERS or not model:
            raise ValueError(f"not a provider:model pair: {part!r}")
        refs.append(ModelRef(provider, model))
    return refs


def extract_json(text: str) -> str:
    """The JSON object in a reply, without a Markdown fence or words around it."""
    stripped = text.strip()
    if fenced := FENCE.match(stripped):
        stripped = fenced.group(1)
    start, end = stripped.find("{"), stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the reply")
    return stripped[start : end + 1]


def json_instructions(schema: type[BaseModel]) -> str:
    return (
        "Answer with one JSON object and nothing else: no Markdown, no explanation. "
        f"It must match this JSON Schema:\n{json.dumps(schema.model_json_schema())}"
    )


class Router:
    def __init__(
        self,
        chains: dict[str, list[ModelRef]],
        make_model: Callable[[ModelRef], BaseChatModel],
        ledger: Ledger,
        *,
        limits: dict[str, DailyLimit] | None = None,
        callbacks: Sequence[BaseCallbackHandler] = (),
    ) -> None:
        self.chains = chains
        self._make_model = make_model
        self._ledger = ledger
        self._limits = limits or {}
        self._callbacks = list(callbacks)
        self._gates = {name: asyncio.Semaphore(n) for name, n in CONCURRENCY.items()}

    async def structured[T: BaseModel](
        self, role: str, schema: type[T], *, system: str, user: str, run_id: int | None = None
    ) -> T:
        messages: list[BaseMessage] = [
            SystemMessage(f"{system}\n\n{json_instructions(schema)}"),
            HumanMessage(user),
        ]
        attempts: list[str] = []
        for position, ref in enumerate(self.chains[role]):
            limit = self._limits.get(ref.provider)
            if limit and not limit.allows(await self._ledger.usage_today(ref.provider)):
                attempts.append(f"{ref}: daily budget used")
                continue
            result = await self._try_model(role, ref, schema, messages, run_id, position > 0)
            if isinstance(result, str):
                attempts.append(f"{ref}: {result}")
                continue
            return result
        raise ModelsExhaustedError(role, attempts)

    async def stream(
        self, role: str, *, system: str, user: str, run_id: int | None = None
    ) -> AsyncIterator[str]:
        """Plain text as the model writes it. It falls back to the next model only before
        the first piece arrives; after that the text is already on the reader's screen."""
        messages: list[BaseMessage] = [SystemMessage(system), HumanMessage(user)]
        attempts: list[str] = []
        for position, ref in enumerate(self.chains[role]):
            limit = self._limits.get(ref.provider)
            if limit and not limit.allows(await self._ledger.usage_today(ref.provider)):
                attempts.append(f"{ref}: daily budget used")
                continue
            started = time.monotonic()
            reply: AIMessageChunk | None = None
            try:
                model = self._make_model(ref)
                async with self._gates.get(ref.provider, asyncio.Semaphore(1)):
                    config = self._config(role, ref, run_id)
                    async for chunk in model.astream(messages, config=config):
                        reply = chunk if reply is None else reply + chunk
                        if chunk.text:
                            yield chunk.text
            except Exception as error:  # rate limit, quota, timeout, auth, missing key
                await self._record(run_id, role, ref, reply, started, position > 0, describe(error))
                log.warning("model_failed", role=role, model=str(ref), error=describe(error))
                if reply is not None and reply.text:
                    raise  # part of the answer is out; the next model cannot continue it
                attempts.append(f"{ref}: {type(error).__name__}")
                continue
            await self._record(run_id, role, ref, reply, started, position > 0, "")
            return
        raise ModelsExhaustedError(role, attempts)

    async def _try_model[T: BaseModel](
        self,
        role: str,
        ref: ModelRef,
        schema: type[T],
        messages: list[BaseMessage],
        run_id: int | None,
        fell_back: bool,
    ) -> T | str:
        """The validated answer, or why this model failed."""
        conversation = list(messages)
        started = time.monotonic()
        try:
            model = self._make_model(ref)
        except Exception as error:  # a missing key or an unknown provider
            await self._record(run_id, role, ref, None, started, fell_back, describe(error))
            return f"{type(error).__name__}"
        for _ in range(2):  # the first answer, then one repair
            started = time.monotonic()
            try:
                async with self._gates.get(ref.provider, asyncio.Semaphore(1)):
                    reply = await model.ainvoke(
                        conversation, config=self._config(role, ref, run_id)
                    )
            except Exception as error:  # rate limit, quota, timeout, auth: try the next model
                await self._record(run_id, role, ref, None, started, fell_back, describe(error))
                log.warning("model_failed", role=role, model=str(ref), error=describe(error))
                return f"{type(error).__name__}"
            try:
                value = schema.model_validate_json(extract_json(reply.text))
            except (ValueError, ValidationError) as error:
                await self._record(run_id, role, ref, reply, started, fell_back, "invalid output")
                conversation += [
                    reply,
                    HumanMessage(f"That reply was not valid: {error}. Send the corrected JSON."),
                ]
                continue
            await self._record(run_id, role, ref, reply, started, fell_back, "")
            return value
        return "invalid output twice"

    def _config(self, role: str, ref: ModelRef, run_id: int | None) -> RunnableConfig:
        return {
            "callbacks": self._callbacks,
            "run_name": role,
            "metadata": {"role": role, "model": str(ref), "run_id": run_id},
        }

    async def _record(
        self,
        run_id: int | None,
        role: str,
        ref: ModelRef,
        reply: BaseMessage | None,
        started: float,
        fell_back: bool,
        error: str,
    ) -> None:
        usage = reply.usage_metadata if isinstance(reply, AIMessage) else None
        await self._ledger.record(
            run_id,
            CallRecord(
                role=role,
                provider=ref.provider,
                model=ref.model,
                input_tokens=usage["input_tokens"] if usage else 0,
                output_tokens=usage["output_tokens"] if usage else 0,
                latency_ms=round((time.monotonic() - started) * 1000),
                ok=not error,
                fell_back=fell_back,
                error=error,
            ),
        )
