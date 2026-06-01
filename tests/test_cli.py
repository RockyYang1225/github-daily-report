from datetime import date, timedelta
from pathlib import Path

from typer.testing import CliRunner

import github_daily_report.cli as cli
from github_daily_report.cli import app
from github_daily_report.mailer import MailError
from github_daily_report.summarizer import SummarizerError


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
    recent_report = reports / f"{(date.today() - timedelta(days=1)).isoformat()}.md"
    recent_report.write_text("[old](https://github.com/acme/agent-kit)", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")

    result = runner.invoke(
        app,
        ["dry-run", "--config", str(config_path), "--output-dir", str(reports), "--use-fixtures"],
    )

    assert result.exit_code == 0
    generated_reports = [path for path in reports.glob("*.md") if path != recent_report]
    assert generated_reports
    markdown = generated_reports[0].read_text(encoding="utf-8")
    assert "https://github.com/acme/agent-kit" not in markdown


def test_dry_run_writes_fallback_report_when_openrouter_fails(tmp_path, monkeypatch):
    runner = CliRunner()
    config_path = tmp_path / "sources.yml"
    config_path.write_text(
        "report: {title: AI Daily, timezone: Asia/Shanghai, language: zh-CN}\n"
        "limits: {per_source: 2, final_items: 3}\n"
        "keywords: [AI]\n"
        "rss_feeds: []\n"
        "sources: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")
    monkeypatch.setattr(
        cli.OpenRouterSummarizer,
        "summarize",
        lambda self, items: (_ for _ in ()).throw(SummarizerError("temporary outage")),
    )
    monkeypatch.setattr(
        cli,
        "_collect_live_results",
        lambda config: cli._collect_fixture_results(),
    )

    result = runner.invoke(
        app,
        ["dry-run", "--config", str(config_path), "--output-dir", str(tmp_path / "reports")],
    )

    assert result.exit_code == 0
    markdown = next(Path(tmp_path / "reports").glob("*.md")).read_text(encoding="utf-8")
    assert "基础版" in markdown
    assert "OpenRouter summarization failed" in markdown


def test_run_keeps_written_report_when_email_delivery_fails(tmp_path, monkeypatch):
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
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "password")
    monkeypatch.setenv("MAIL_FROM", "from@example.com")
    monkeypatch.setenv("MAIL_TO", "to@example.com")
    monkeypatch.setattr(
        cli,
        "send_report_email",
        lambda payload, smtp_config, dry_run=False: (_ for _ in ()).throw(MailError("smtp outage")),
    )

    result = runner.invoke(
        app,
        ["run", "--config", str(config_path), "--output-dir", str(tmp_path / "reports"), "--use-fixtures"],
    )

    assert result.exit_code == 1
    assert list(Path(tmp_path / "reports").glob("*.md"))
    assert "Report written but email delivery failed" in result.output
