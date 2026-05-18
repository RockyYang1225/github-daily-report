from datetime import date, datetime, timezone

from github_daily_report.models import DailyReport, ReportContent
from github_daily_report.models import ReportItem
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


def test_render_html_renders_collapsible_item_introduction(sample_items):
    sample_items[0].summary_zh = "一个用于构建 Agent 工作流的工具包。"
    sample_items[0].detail_zh = "这个项目把工具调用、状态管理和任务编排放在一起，适合快速验证 Agent 原型。"
    report = DailyReport.for_test(sample_items[:1])

    html = render_html(report)

    assert "<details" in html
    assert "<summary" in html
    assert "查看详细介绍" in html
    assert "#detail-acme-agent-kit" not in html
    assert "这个项目把工具调用、状态管理和任务编排放在一起" in html


def test_rendering_enforces_section_item_limits():
    def item(name: str, category: str = "github") -> ReportItem:
        return ReportItem(
            title=f"demo/{name}",
            url=f"https://github.com/demo/{name}",
            source="GitHub",
            category=category,
            summary=f"Project {name}",
            published_at=datetime(2026, 5, 14, tzinfo=timezone.utc),
        )

    today_items = [item(f"today-{index}") for index in range(12)]
    github_items = [item(f"github-{index}") for index in range(7)]
    report = DailyReport(
        report_date=date(2026, 5, 14),
        content=ReportContent(
            executive_summary="今天值得关注三件事。",
            sections={"今日必看": today_items, "GitHub 热门项目": github_items},
            recommendations=[],
        ),
    )

    markdown = render_markdown(report)
    html = render_html(report)

    assert "today-9" in markdown
    assert "today-10" not in markdown
    assert "github-4" in markdown
    assert "github-5" not in markdown
    assert "today-9" in html
    assert "today-10" not in html
    assert "github-4" in html
    assert "github-5" not in html
