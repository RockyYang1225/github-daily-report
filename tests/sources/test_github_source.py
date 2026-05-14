import json
from pathlib import Path

from github_daily_report.sources.github import parse_github_search


def test_parse_github_search_fixture():
    data = json.loads(Path("tests/fixtures/github_search.json").read_text())

    items = parse_github_search(data, source_name="GitHub AI Search")

    assert items[0].title == "acme/agent-kit"
    assert items[0].category == "github"
    assert items[0].score_signals["stars"] == 1234
