from __future__ import annotations

from html import escape
from typing import Iterable, List

from github_daily_report.models import DailyReport, ReportItem


SECTION_ORDER = [
    "今日必看",
    "GitHub 热门项目",
    "模型与数据集",
    "论文与代码",
    "AI 开发者资讯",
    "Skills / Agents / 工具动态",
    "今日行动建议",
    "抓取状态与失败来源",
]


def _item_markdown(item: ReportItem) -> str:
    tags = f" `{'`, `'.join(item.tags)}`" if item.tags else ""
    lines = [f"- [{item.title}]({item.url}){tags}"]
    lines.append(f"  来源：{item.source}")
    summary = item.summary_zh or item.summary
    if summary:
        lines.append(f"  说明：{summary}")
    if item.why_it_matters:
        lines.append(f"  值得关注：{item.why_it_matters}")
    if item.action_suggestion:
        lines.append(f"  建议：{item.action_suggestion}")
    return "\n".join(lines)


def render_markdown(report: DailyReport) -> str:
    lines: List[str] = [
        f"# AI 开发者日报 - {report.report_date.isoformat()}",
        "",
        report.content.executive_summary,
        "",
    ]

    for section in SECTION_ORDER:
        lines.extend([f"## {section}", ""])
        if section == "今日行动建议":
            recommendations = report.content.recommendations
            if recommendations:
                lines.extend(f"- {entry}" for entry in recommendations)
            else:
                lines.append("- 今天没有额外行动建议。")
        elif section == "抓取状态与失败来源":
            if report.source_warnings:
                lines.extend(f"- {warning}" for warning in report.source_warnings)
            else:
                lines.append("- 所有启用的数据源抓取正常。")
        else:
            items = report.content.sections.get(section, [])
            if items:
                lines.extend(_item_markdown(item) for item in items)
            else:
                lines.append("- 暂无入选内容。")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _item_html(item: ReportItem) -> str:
    tags = " ".join(
        f'<span style="font-size:12px;color:#4f46e5;background:#eef2ff;padding:2px 6px;border-radius:4px;">{escape(tag)}</span>'
        for tag in item.tags
    )
    summary = item.summary_zh or item.summary
    why = (
        f'<div style="color:#111827;margin-top:4px;"><strong>值得关注：</strong>{escape(item.why_it_matters)}</div>'
        if item.why_it_matters
        else ""
    )
    action = (
        f'<div style="color:#111827;margin-top:4px;"><strong>建议：</strong>{escape(item.action_suggestion)}</div>'
        if item.action_suggestion
        else ""
    )
    return (
        '<li style="margin:0 0 12px 0;">'
        f'<a href="{escape(item.url)}" style="color:#2563eb;text-decoration:none;font-weight:600;">{escape(item.title)}</a>'
        f'<div style="color:#6b7280;margin-top:4px;">来源：{escape(item.source)}</div>'
        f'<div style="color:#374151;margin-top:4px;">{escape(summary)}</div>'
        f"{why}"
        f"{action}"
        f'<div style="margin-top:6px;">{tags}</div>'
        "</li>"
    )


def _list_html(items: Iterable[str]) -> str:
    return "<ul style=\"padding-left:20px;margin:0;\">" + "".join(items) + "</ul>"


def render_html(report: DailyReport) -> str:
    section_html: List[str] = []
    for section in SECTION_ORDER:
        section_html.append(f'<h2 style="font-size:20px;margin:28px 0 12px;color:#111827;">{escape(section)}</h2>')
        if section == "今日行动建议":
            entries = report.content.recommendations or ["今天没有额外行动建议。"]
            section_html.append(_list_html(f"<li>{escape(entry)}</li>" for entry in entries))
        elif section == "抓取状态与失败来源":
            entries = report.source_warnings or ["所有启用的数据源抓取正常。"]
            section_html.append(_list_html(f"<li>{escape(entry)}</li>" for entry in entries))
        else:
            items = report.content.sections.get(section, [])
            if items:
                section_html.append(_list_html(_item_html(item) for item in items))
            else:
                section_html.append('<p style="color:#6b7280;margin:0;">暂无入选内容。</p>')

    return (
        '<html><body style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;'
        'line-height:1.6;color:#111827;background:#f9fafb;margin:0;padding:24px;">'
        '<main style="max-width:760px;margin:0 auto;background:#ffffff;padding:28px;border:1px solid #e5e7eb;">'
        f'<h1 style="font-size:26px;margin:0 0 16px;">AI 开发者日报 - {report.report_date.isoformat()}</h1>'
        f'<p style="font-size:15px;color:#374151;">{escape(report.content.executive_summary)}</p>'
        + "".join(section_html)
        + "</main></body></html>"
    )
