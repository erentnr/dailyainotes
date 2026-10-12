"""A topic's daily edition: Scout picks the stories, then each picked story runs its story
graph until the note waits for the owner. A fixed sequence, so a function, not a graph.

Reruns are safe: a finished edition is skipped, Scout runs only until it has ranked the
edition, and a story graph that stopped part-way resumes from its last checkpoint.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from dailyainotes.db import editorial as db
from dailyainotes.db.engine import AsyncEngine
from dailyainotes.db.runs import finish_run, start_run
from dailyainotes.domain.editorial import slugify
from dailyainotes.graphs.scout import ScoutDeps, build_scout
from dailyainotes.graphs.story import StoryDeps, StoryState, build_story_graph
from dailyainotes.llm.router import ModelsExhaustedError

# INTENT.md, Performance and Cost: at most 2 notes per topic and 15 a day.
STORIES_PER_TOPIC = 2
STORIES_PER_DAY = 15


@dataclass
class EditionReport:
    slug: str
    # done, skipped (it was done before) or failed (a story's models were exhausted).
    status: str = "done"
    collected: int = 0
    stories: int = 0
    waiting: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


async def run_edition(
    scout_deps: ScoutDeps,
    story_deps: StoryDeps,
    saver: BaseCheckpointSaver[Any],
    *,
    topic_id: int,
    slug: str,
    day: date,
) -> EditionReport:
    engine = scout_deps.engine
    report = EditionReport(slug)
    edition_id, status = await db.start_edition(engine, topic_id, day)
    if status == "done":
        report.status = "skipped"
        return report

    story_ids = await db.picked_stories(engine, edition_id)
    if not story_ids:
        room = STORIES_PER_DAY - await db.picked_on(engine, day)
        thread_id = f"edition:{slug}:{day.isoformat()}"
        run_id = await start_run(engine, "edition", topic_id=topic_id, thread_id=thread_id)
        scouted = await build_scout(scout_deps, saver).ainvoke(
            {
                "topic_id": topic_id,
                "slug": slug,
                "edition_id": edition_id,
                "cap": max(0, min(STORIES_PER_TOPIC, room)),
            },
            {"configurable": {"thread_id": thread_id}},
        )
        await finish_run(engine, run_id, "done")
        report.collected, report.stories = scouted["collected"], scouted["stories"]
        story_ids = scouted["picked"]

    graph = build_story_graph(story_deps, saver)
    for story_id in story_ids:
        try:
            note_id = await write_note(graph, engine, story_id)
        except ModelsExhaustedError as error:
            report.errors.append(f"story {story_id}: {error}")
            continue
        if note_id is not None:
            report.waiting.append(note_id)

    report.status = "failed" if report.errors else "done"
    stats = {
        "collected": report.collected,
        "stories": report.stories,
        "picked": len(story_ids),
        "waiting": len(report.waiting),
        "errors": report.errors,
    }
    await db.finish_edition(engine, edition_id, report.status, stats)
    return report


async def write_note(
    graph: CompiledStateGraph[StoryState, None, StoryState, StoryState],
    engine: AsyncEngine,
    story_id: int,
) -> int | None:
    """Run the story's graph until its note waits for review; the note's id, or None when it
    was already decided."""
    existing = await db.note_for_story(engine, story_id)
    if existing and existing[1] != "drafting":
        return existing[0] if existing[1] == "awaiting_approval" else None

    thread_id = f"note:{story_id}"
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    checkpoint = await graph.aget_state(config)
    start: StoryState | None
    if existing and checkpoint.values:
        # Resume where the last attempt stopped, under the same run.
        note_id, run_id, start = existing[0], checkpoint.values["run_id"], None
    else:
        topic_id, title, day = await db.story_header(engine, story_id)
        note_id = await db.create_note(
            engine, story_id, topic_id, day, slugify(title, day), thread_id
        )
        run_id = await start_run(engine, "story", topic_id=topic_id, thread_id=thread_id)
        start = {"story_id": story_id, "note_id": note_id, "run_id": run_id}
    try:
        await graph.ainvoke(start, config)
    except ModelsExhaustedError as error:
        await finish_run(engine, run_id, "failed", str(error))
        raise
    await finish_run(engine, run_id, "waiting")
    return note_id
