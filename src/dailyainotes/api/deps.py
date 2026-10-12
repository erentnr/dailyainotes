"""What the routers share: the embedding model and the model router, made on first use, since
loading the embedding model takes a second and most requests never need it."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from dailyainotes.ask import AskDeps
from dailyainotes.db.runs import DbLedger
from dailyainotes.graphs.story import StoryDeps
from dailyainotes.llm.embeddings import LocalEmbeddings
from dailyainotes.llm.providers import build_router
from dailyainotes.llm.router import Router


@dataclass(frozen=True)
class Models:
    embeddings: LocalEmbeddings
    router: Router


def models(request: Request) -> Models:
    state = request.app.state
    if state.models is None:
        embeddings = LocalEmbeddings(state.settings.embedding_cache_dir)
        state.models = Models(embeddings, build_router(state.settings, DbLedger(state.engine)))
    found: Models = state.models
    return found


def ask_deps(request: Request, loaded: Annotated[Models, Depends(models)]) -> AskDeps:
    return AskDeps(request.app.state.engine, loaded.embeddings, loaded.router)


def story_deps(request: Request, loaded: Annotated[Models, Depends(models)]) -> StoryDeps:
    return StoryDeps(request.app.state.engine, loaded.router, loaded.embeddings)
