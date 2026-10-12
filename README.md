# Daily AI Notes

AI takes notes on what's happening, every day, on the things you care about.

Every day, LangGraph agents collect coverage for each topic in a fixed catalog, cluster duplicate reports into stories, research them, write short notes with inline citations, fact-check every claim and wait for a human approval before publishing. Visitors read the notes for the topics they pick and ask questions answered only from the notes, with citations.

**Status:** proof of concept, under construction ([ADR 0001](docs/adr/0001-proof-of-concept-scope.md)). The milestones are listed in [INTENT.md](INTENT.md).

## Development

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14.

```sh
uv sync
cp .env.example .env
make check   # format, lint, types, tests
```

## How this repository is run

- [AGENTS.md](AGENTS.md): how humans and coding agents work here
- [INTENT.md](INTENT.md): rules and standing tasks
- [MEMORY.md](MEMORY.md): what has been learned, with sources
- [DESIGN.md](DESIGN.md): the visual system

## License

[Apache-2.0](LICENSE)
