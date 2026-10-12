from dailyainotes.sources.urls import canonical_url, registrable_domain, url_hash


def test_canonical_url_drops_tracking_parameters_and_the_fragment() -> None:
    url = "HTTPS://Example.COM/news/a?utm_source=x&id=7&fbclid=y#comments"

    assert canonical_url(url) == "https://example.com/news/a?id=7"


def test_the_same_story_with_and_without_tracking_has_one_hash() -> None:
    assert url_hash("https://example.com/a?utm_medium=rss") == url_hash("https://example.com/a")


def test_registrable_domain_handles_multi_part_suffixes() -> None:
    assert registrable_domain("https://feeds.bbci.co.uk/sport/rss.xml") == "bbci.co.uk"
    assert registrable_domain("https://www.formula1.com/en/latest") == "formula1.com"
