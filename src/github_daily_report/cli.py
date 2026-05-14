from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List

import typer

from github_daily_report.config import EnvConfig, load_env_config, load_public_config
from github_daily_report.mailer import EmailMessagePayload, SmtpConfig, send_report_email
from github_daily_report.models import DailyReport, ReportItem, SourceResult
from github_daily_report.ranking import rank_items
from github_daily_report.rendering import render_html, render_markdown
from github_daily_report.sources.github import GitHubSearchSource, fixture_items
from github_daily_report.sources.huggingface import HuggingFaceSource
from github_daily_report.sources.papers import ArxivSource, PapersWithCodeSource
from github_daily_report.sources.rss import RssSource
from github_daily_report.sources.skills import SkillsSource
from github_daily_report.summarizer import FixtureSummarizer, OpenRouterSummarizer

app = typer.Typer(help="Generate and send the AI developer daily report.")


def _collect_fixture_results() -> List[SourceResult]:
    return [
        SourceResult(source="fixtures", items=fixture_items()),
        HuggingFaceSource().fetch(),
        ArxivSource().fetch(),
        PapersWithCodeSource().fetch(),
        SkillsSource().fetch(),
    ]


def _collect_live_results(config) -> List[SourceResult]:
    results: List[SourceResult] = []
    if config.sources.get("github", True):
        for query in config.github_queries[: max(config.limits.per_source, 1)]:
            results.append(GitHubSearchSource(query, limit=config.limits.per_source).fetch())
    if config.sources.get("huggingface", True):
        results.append(HuggingFaceSource().fetch())
    if config.sources.get("papers", True):
        results.extend([ArxivSource().fetch(), PapersWithCodeSource().fetch()])
    if config.sources.get("skills", True):
        results.append(SkillsSource().fetch())
    if config.sources.get("rss", True):
        for feed in config.rss_feeds:
            results.append(RssSource(feed.name, feed.url, limit=config.limits.per_source).fetch())
    return results


def _write_report(report: DailyReport, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{report.report_date.isoformat()}.md"
    path.write_text(report.markdown, encoding="utf-8")
    return path


def _build_report(config_path: Path, output_dir: Path, use_fixtures: bool, send_email: bool) -> DailyReport:
    public_config = load_public_config(config_path)
    env_config = load_env_config(send_email=send_email)
    results = _collect_fixture_results() if use_fixtures else _collect_live_results(public_config)
    warnings = [warning for result in results for warning in result.warnings]
    items: List[ReportItem] = [item for result in results for item in result.items]
    ranked = rank_items(items, public_config.limits.final_items)

    if use_fixtures:
        content = FixtureSummarizer().summarize(ranked)
    else:
        content = OpenRouterSummarizer(
            api_key=env_config.openrouter_api_key,
            model=env_config.openrouter_model,
            base_url=env_config.openrouter_base_url,
        ).summarize(ranked)

    report = DailyReport(report_date=date.today(), content=content, source_warnings=warnings)
    report.markdown = render_markdown(report)
    report.html = render_html(report)
    _write_report(report, output_dir)
    return report


def _smtp_config(env_config: EnvConfig) -> SmtpConfig:
    return SmtpConfig(
        host=env_config.smtp_host or "",
        port=env_config.smtp_port or 587,
        username=env_config.smtp_username or "",
        password=env_config.smtp_password or "",
    )


@app.command("dry-run")
def dry_run(
    config: Path = typer.Option(Path("config/sources.yml"), "--config"),
    output_dir: Path = typer.Option(Path("reports"), "--output-dir"),
    use_fixtures: bool = typer.Option(False, "--use-fixtures"),
):
    report = _build_report(config, output_dir, use_fixtures=use_fixtures, send_email=False)
    typer.echo(f"Report written: {output_dir / (report.report_date.isoformat() + '.md')}")


@app.command("run")
def run(
    config: Path = typer.Option(Path("config/sources.yml"), "--config"),
    output_dir: Path = typer.Option(Path("reports"), "--output-dir"),
    use_fixtures: bool = typer.Option(False, "--use-fixtures"),
):
    report = _build_report(config, output_dir, use_fixtures=use_fixtures, send_email=True)
    env_config = load_env_config(send_email=True)
    payload = EmailMessagePayload(
        subject=f"AI 开发者日报 - {report.report_date.isoformat()}",
        html=report.html,
        sender=env_config.mail_from or "",
        recipients=env_config.recipients,
    )
    send_report_email(payload, _smtp_config(env_config), dry_run=False)
    typer.echo("Report sent.")
