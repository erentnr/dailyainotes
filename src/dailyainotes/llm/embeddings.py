"""Local embeddings: BAAI/bge-small-en-v1.5 on the CPU through fastembed (ONNX Runtime).

LangChain's own fastembed class lives only in langchain-community, which INTENT.md rules out,
so this is a small adapter on LangChain's `Embeddings` interface. Its async methods run the
model in a thread.
"""

from fastembed import TextEmbedding
from langchain_core.embeddings import Embeddings

from dailyainotes.domain.embedding import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL


class LocalEmbeddings(Embeddings):
    def __init__(self, cache_dir: str | None = None) -> None:
        # Downloads the model (64 MB) into cache_dir the first time.
        self._model = TextEmbedding(EMBEDDING_MODEL, cache_dir=cache_dir)
        if self._model.embedding_size != EMBEDDING_DIMENSIONS:
            raise RuntimeError(f"{EMBEDDING_MODEL} no longer has {EMBEDDING_DIMENSIONS} dimensions")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.passage_embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        vector = next(iter(self._model.query_embed(text)))
        return list(vector.tolist())
