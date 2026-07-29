from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Dict, List, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, StringConstraints, field_validator

from github_daily_report.history import load_seen_urls
from github_daily_report.models import DailyReport, ReportItem, SourceResult
from github_daily_report.ranking import normalize_item_url, rank_items
from github_daily_report.rendering import render_html, render_markdown
from github_daily_report.summarizer import build_report_content


EditorialText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _require_chinese(value: str) -> str:
    if not any("\u4e00" <= character <= "\u9fff" for character in value):
        raise ValueError("Chinese text is required")
    return value


class CandidateBatch(BaseModel):
    report_date: date
    timezone: str
    source_warnings: List[str] = Field(default_factory=list)
    items: List[ReportItem] = Field(default_factory=list)


class ItemEnrichment(BaseModel):
    summary_zh: EditorialText
    why_it_matters: EditorialText
    action_suggestion: EditorialText
    detail_zh: EditorialText

    @field_validator("summary_zh", "why_it_matters", "action_suggestion", "detail_zh")
    @classmethod
    def require_chinese(cls, value: str) -> str:
        return _require_chinese(value)


class CodexReportDraft(BaseModel):
    executive_summary: EditorialText
    recommendations: List[EditorialText] = Field(min_length=1)
    item_enrichments: Dict[str, ItemEnrichment]

    @field_validator("executive_summary")
    @classmethod
    def require_chinese_summary(cls, value: str) -> str:
        return _require_chinese(value)

    @field_validator("recommendations")
    @classmethod
    def require_chinese_recommendations(cls, values: List[str]) -> List[str]:
        return [_require_chinese(value) for value in values]


def current_report_date(timezone_name: str, now: Optional[datetime] = None) -> date:
    current = now or datetime.now(tz=ZoneInfo("UTC"))
    return current.astimezone(ZoneInfo(timezone_name)).date()


def build_candidate_batch(
    results: List[SourceResult],
    reports_dir: Path,
    report_date: date,
    timezone_name: str,
    lookback_days: int,
    final_items: int,
) -> CandidateBatch:
    warnings = [warning for result in results for warning in result.warnings]
    items = [item for result in results for item in result.items]
    seen = load_seen_urls(reports_dir, today=report_date, lookback_days=lookback_days)
    warnings.extend(seen.warnings)
    ranked = rank_items(items, final_items, seen_urls=seen.urls)
    return CandidateBatch(
        report_date=report_date,
        timezone=timezone_name,
        source_warnings=warnings,
        items=ranked,
    )


def build_codex_report(batch: CandidateBatch, draft: CodexReportDraft) -> DailyReport:
    candidate_urls = {normalize_item_url(item.url) for item in batch.items}
    enrichment_urls = {normalize_item_url(url) for url in draft.item_enrichments}
    missing = sorted(candidate_urls - enrichment_urls)
    if missing:
        raise ValueError(f"Missing Codex enrichment for: {', '.join(missing)}")

    content = build_report_content(batch.items, draft.model_dump())
    report = DailyReport(
        report_date=batch.report_date,
        content=content,
        source_warnings=batch.source_warnings,
    )
    report.markdown = render_markdown(report)
    report.html = render_html(report)
    return report
