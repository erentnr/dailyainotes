from pathlib import Path

import pytest
from pydantic import ValidationError

from dailyainotes.ingestion.catalog import (
    Catalog,
    load_catalog,
    locator,
    publisher_domain,
)


def test_the_committed_catalog_has_twelve_topics_with_unique_slugs() -> None:
    catalog = load_catalog()

    slugs = [topic.slug for topic in catalog.topics]
    assert len(slugs) == 12
    assert len(set(slugs)) == 12


def test_the_two_starter_topics_have_sources() -> None:
    catalog = load_catalog()

    with_sources = {topic.slug for topic in catalog.topics if topic.sources}
    assert with_sources == {"formula-1", "open-weight-ai-models"}


def test_each_source_type_has_a_locator_and_a_publisher() -> None:
    catalog = Catalog.model_validate(
        {
            "topics": [
                {
                    "slug": "demo",
                    "name": "Demo",
                    "description": "d",
                    "sources": [
                        {"type": "rss", "url": "https://feeds.bbci.co.uk/sport/rss.xml"},
                        {"type": "arxiv", "query": "cat:astro-ph.EP"},
                        {"type": "github_releases", "repo": "vllm-project/vllm"},
                        {"type": "hackernews", "query": "open weights"},
                    ],
                }
            ]
        }
    )

    sources = catalog.topics[0].sources
    assert [locator(s) for s in sources] == [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "cat:astro-ph.EP",
        "vllm-project/vllm",
        "open weights",
    ]
    assert [publisher_domain(s) for s in sources] == [
        "bbci.co.uk",
        "arxiv.org",
        "github.com/vllm-project",
        None,
    ]


@pytest.mark.parametrize(
    "topic",
    [
        {"slug": "Not A Slug", "name": "x", "description": "x"},
        {"slug": "x", "name": "x", "description": "x", "colour": "red"},
        {"slug": "x", "name": "x", "description": "x", "sources": [{"type": "telegram"}]},
        {
            "slug": "x",
            "name": "x",
            "description": "x",
            "sources": [{"type": "rss", "url": "http://a.b"}],
        },
    ],
)
def test_a_malformed_topic_is_rejected(topic: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Catalog.model_validate({"topics": [topic]})


def test_a_catalog_file_is_read_from_toml(tmp_path: Path) -> None:
    path = tmp_path / "catalog.toml"
    path.write_text('[[topics]]\nslug = "a"\nname = "A"\ndescription = "d"\n')

    assert load_catalog(path).topics[0].slug == "a"
