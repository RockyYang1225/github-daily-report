import json
from datetime import date, timedelta
from pathlib import Path

from typer.testing import CliRunner

import github_daily_report.cli as cli
from github_daily_report.cli import app
from github_daily_report.codex_pipeline import CandidateBatch, CodexReportDraft
from github_daily_report.mailer import MailError
from github_daily_report.summarizer import SummarizerError


def _write_test_config(tmp_path: Path) -> Path:
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
    return config_path


def test_collect_exports_candidates_without_secret_env(tmp_path, monkeypatch):
    runner = CliRunner()
    config_path = _write_test_config(tmp_path)
    output_path = tmp_path / "candidates.json"
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)

    result = runner.invoke(
        app,
        [
            "collect",
            "--config",
            str(config_path),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--output",
            str(output_path),
            "--use-fixtures",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["timezone"] == "Asia/Shanghai"
    assert payload["items"]


def test_dry_run_uses_configured_timezone_report_date(tmp_path, monkeypatch):
    runner = CliRunner()
    config_path = _write_test_config(tmp_path)
    reports_dir = tmp_path / "reports"
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    monkeypatch.setenv("OPENROUTER_MODEL", "test-model")
    monkeypatch.setattr(cli, "current_report_date", lambda timezone_name: date(2030, 1, 2))

    result = runner.invoke(
        app,
        [
            "dry-run",
            "--config",
            str(config_path),
            "--output-dir",
            str(reports_dir),
            "--use-fixtures",
        ],
    )

    assert result.exit_code == 0
    assert (reports_dir / "2030-01-02.md").exists()


def test_render_codex_writes_markdown_and_html(tmp_path, sample_items):
    candidates_path = tmp_path / "candidates.json"
    draft_path = tmp_path / "draft.json"
    html_path = tmp_path / "report.html"
    reports_dir = tmp_path / "reports"
    batch = CandidateBatch(
        report_date="2026-07-29",
        timezone="Asia/Shanghai",
        items=sample_items,
    )
    draft = CodexReportDraft(
        executive_summary="今天重点关注 Agent 工具。",
        recommendations=["运行一个最小示例。"],
        item_enrichments={
            item.url: {
                "summary_zh": f"{item.title} 的中文介绍。",
                "why_it_matters": "适合快速验证。",
                "action_suggestion": "阅读文档并运行示例。",
                "detail_zh": "适合希望理解项目能力的开发者。",
            }
            for item in sample_items
        },
    )
    candidates_path.write_text(batch.model_dump_json(indent=2), encoding="utf-8")
    draft_path.write_text(draft.model_dump_json(indent=2), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "render-codex",
            "--candidates",
            str(candidates_path),
            "--draft",
            str(draft_path),
            "--output-dir",
            str(reports_dir),
            "--html-output",
            str(html_path),
        ],
    )

    assert result.exit_code == 0
    assert (reports_dir / "2026-07-29.md").exists()
    assert "<html" in html_path.read_text(encoding="utf-8")


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
