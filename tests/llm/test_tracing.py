from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from dailyainotes.llm.tracing import model_spans


def spans_of(scope: str) -> list[bool]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    with provider.get_tracer(scope).start_as_current_span("tools/call search_notes") as span:
        span.set_attribute("gen_ai.operation.name", "execute_tool")
    return [model_spans(s) for s in exporter.get_finished_spans()]


def test_mcp_tool_calls_stay_out_of_langfuse_though_they_look_like_gen_ai() -> None:
    assert spans_of("mcp-python-sdk") == [False]


def test_other_gen_ai_spans_are_still_exported() -> None:
    assert spans_of("opentelemetry.instrumentation.langchain") == [True]
