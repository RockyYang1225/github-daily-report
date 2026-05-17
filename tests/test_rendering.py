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


def test_render_markdown_includes_chinese_item_explanation(sample_items):
    sample_items[0].summary_zh = "一个用于构建 Agent 工作流的工具包。"
    sample_items[0].why_it_matters = "适合快速验证工具调用和状态管理。"
    report = DailyReport.for_test(sample_items)

    markdown = render_markdown(report)

    assert "来源：GitHub" in markdown
    assert "中文介绍：一个用于构建 Agent 工作流的工具包。" in markdown
    assert "值得关注：适合快速验证工具调用和状态管理。" in markdown


def test_render_markdown_uses_chinese_fallback_when_item_lacks_enrichment(sample_items):
    sample_items[0].summary = "The fastest repo in history to surpass 100K stars."
    report = DailyReport.for_test(sample_items[:1])

    markdown = render_markdown(report)

    assert "中文介绍：这是一个来自 GitHub 的 github 项目，原始描述为：The fastest repo in history to surpass 100K stars." in markdown
