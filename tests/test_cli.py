from pathlib import Path

from typer.testing import CliRunner

from github_daily_report.cli import app


def test_dry_run_writes_markdown_without_email(tmp_path, monkeypatch):
    runner = CliRunner()
    config_path = tmp_path / "sources.yml"
    config_path.write_text(
        "report: {title: AI Daily, timezone: Asia/Shanghai, language: zh-CN}\n"
        "limits: {per_source: 2, final_items: 3}\n"
        "keywords: [AI]\n"
        "rss_feeds: []\n"
        "sources: {fixtures: true}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")

    result = runner.invoke(
        app,
        ["dry-run", "--config", str(config_path), "--output-dir", str(tmp_path / "reports"), "--use-fixtures"],
    )

    assert result.exit_code == 0
    assert list(Path(tmp_path / "reports").glob("*.md"))


def test_dry_run_uses_history_to_avoid_recent_recommendations(tmp_path, monkeypatch):
    runner = CliRunner()
    config_path = tmp_path / "sources.yml"
    config_path.write_text(
        "report: {title: AI Daily, timezone: Asia/Shanghai, language: zh-CN}\n"
        "limits: {per_source: 2, final_items: 3}\n"
        "history: {lookback_days: 14}\n"
        "keywords: [AI]\n"
        "rss_feeds: []\n"
        "sources: {fixtures: true}\n",
        encoding="utf-8",
    )
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "2026-05-17.md").write_text("[old](https://github.com/acme/agent-kit)", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")

    result = runner.invoke(
        app,
        ["dry-run", "--config", str(config_path), "--output-dir", str(reports), "--use-fixtures"],
    )

    assert result.exit_code == 0
    markdown = next(reports.glob("*.md")).read_text(encoding="utf-8")
    assert "https://github.com/acme/agent-kit" not in markdown
