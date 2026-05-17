import json
from pathlib import Path

from github_daily_report.sources.github import parse_github_search
from github_daily_report.sources.github import parse_github_trending


def test_parse_github_search_fixture():
    data = json.loads(Path("tests/fixtures/github_search.json").read_text())

    items = parse_github_search(data, source_name="GitHub AI Search")

    assert items[0].title == "acme/agent-kit"
    assert items[0].category == "github"
    assert items[0].score_signals["stars"] == 1234


def test_parse_github_trending_fixture():
    html = Path("tests/fixtures/github_trending.html").read_text()

    items = parse_github_trending(html, period="daily")

    assert items[0].title == "acme/agent-kit"
    assert items[0].url == "https://github.com/acme/agent-kit"
    assert items[0].source == "GitHub Trending Daily"
    assert items[0].category == "github"
    assert items[0].summary == "Toolkit for building AI agents."
    assert items[0].tags == ["Python", "trending:daily"]
    assert items[0].score_signals["stars"] == 1234
    assert items[0].score_signals["period_stars"] == 56
