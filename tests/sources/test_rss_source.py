from pathlib import Path

from github_daily_report.sources.rss import parse_rss_feed


def test_parse_rss_feed_fixture():
    xml = Path("tests/fixtures/feed.xml").read_text()

    items = parse_rss_feed(xml, source_name="OpenAI Blog", category="developer-news")

    assert items[0].source == "OpenAI Blog"
    assert items[0].category == "developer-news"
    assert items[0].url.startswith("https://")
