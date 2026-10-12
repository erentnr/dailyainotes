import os

import dailyainotes.llm.embeddings  # noqa: F401  (importing it is the behaviour under test)


def test_onnx_runtime_telemetry_is_off_once_embeddings_are_imported() -> None:
    assert os.environ["ORT_DISABLE_TELEMETRY"] == "1"
