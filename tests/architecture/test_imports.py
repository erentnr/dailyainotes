"""INTENT.md, Architectural Constraints: imports point down only, and vendor packages stay
behind their seam. Every package under src/dailyainotes must be listed in LAYERS or SHARED."""

import ast
from pathlib import Path

PACKAGE = "dailyainotes"
SOURCE = Path(__file__).parents[2] / "src" / PACKAGE

# Highest layer first. A package may import its own layer or the ones below it.
LAYERS: list[set[str]] = [
    {"api", "worker", "cli", "mcp"},  # interfaces
    {"graphs", "ingestion", "ask", "stats", "evals"},  # graphs and services
    {"db", "sources", "llm", "retrieval"},  # adapters
    {"domain"},
]
INTERFACES = LAYERS[0]
# Importable from every layer; they import nothing layered themselves.
SHARED = {"settings", "logging"}
# Third-party packages that only one of our packages may import.
SEAMS = {
    "sqlalchemy": "db",
    "alembic": "db",
    "psycopg": "db",
    "pgvector": "db",
    "httpx2": "sources",
    "feedparser": "sources",
    "tldextract": "sources",
    "trafilatura": "sources",
    "fastembed": "llm",
}


def top_level(path: Path) -> str:
    return path.relative_to(SOURCE).parts[0].removesuffix(".py")


def imports_of(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def layer_of(name: str) -> int:
    for index, layer in enumerate(LAYERS):
        if name in layer:
            return index
    raise AssertionError(f"`{name}` is in no layer: add it to LAYERS or SHARED")


def modules() -> list[Path]:
    return [p for p in SOURCE.rglob("*.py") if p.name != "__init__.py" or p.parent != SOURCE]


def test_every_package_has_a_layer() -> None:
    for path in modules():
        name = top_level(path)
        if name not in SHARED:
            layer_of(name)


def test_imports_point_down_and_interfaces_stay_apart() -> None:
    violations = []
    for path in modules():
        source = top_level(path)
        for imported in imports_of(path):
            parts = imported.split(".")
            if parts[0] != PACKAGE or len(parts) < 2 or parts[1] == source:
                continue
            target = parts[1]
            if target in SHARED:
                continue
            if source in SHARED:
                violations.append(f"{path.name}: shared module imports {imported}")
            elif layer_of(target) < layer_of(source):
                violations.append(f"{path.name}: {source} imports a higher layer, {imported}")
            elif source in INTERFACES and target in INTERFACES:
                violations.append(f"{path.name}: interface {source} imports {imported}")
    assert violations == []


def test_vendor_packages_stay_behind_their_seam() -> None:
    violations = []
    for path in modules():
        source = top_level(path)
        for imported in imports_of(path):
            owner = SEAMS.get(imported.split(".")[0])
            if owner is not None and owner != source:
                violations.append(f"{path.name}: {imported} belongs in {owner}/")
    assert violations == []
