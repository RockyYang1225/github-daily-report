from github_daily_report import cli
from github_daily_report.config import PublicConfig
from github_daily_report.models import SourceResult


def test_collect_live_results_includes_skills_directory_when_enabled(monkeypatch):
    class FakeSkillsDirectorySource:
        def __init__(self, limit):
            self.limit = limit

        def fetch(self):
            return SourceResult(source="skills.sh")

    monkeypatch.setattr(cli, "SkillsDirectorySource", FakeSkillsDirectorySource)

    config = PublicConfig(
        sources={
            "github": False,
            "huggingface": False,
            "papers": False,
            "rss": False,
            "skills": False,
            "skills_directory": True,
        },
    )
    config.github_trending.enabled = False

    results = cli._collect_live_results(config)

    assert [result.source for result in results] == ["skills.sh"]
