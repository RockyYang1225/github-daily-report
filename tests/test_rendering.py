from datetime import date

from github_daily_report.models import DailyReport, ReportContent
from github_daily_report.rendering import render_html, render_markdown


def test_render_markdown_contains_required_sections(sample_items):
    report = DailyReport(
        report_date=date(2026, 5, 14),
        content=ReportContent(
            executive_summary="今天值得关注三件事。",
            sections={"今日必看": sample_items[:1], "今日行动建议": []},
            recommendations=["试用第一个项目"],
        ),
        source_warnings=["RSS timeout"],
    )

    markdown = render_markdown(report)

    assert "# AI 开发者日报 - 2026-05-14" in markdown
    assert "## 今日必看" in markdown
    assert "RSS timeout" in markdown


def test_render_html_is_email_friendly(sample_items):
    report = DailyReport.for_test(sample_items)

    html = render_html(report)

    assert "<html" in html
    assert "style=" in html
    assert sample_items[0].url in html
