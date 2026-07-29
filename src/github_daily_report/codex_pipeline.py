from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from github_daily_report.history import load_seen_urls
from github_daily_report.models import ReportItem, SourceResult
from github_daily_report.ranking import rank_items


class CandidateBatch(BaseModel):
    report_date: date
    timezone: str
    source_warnings: List[str] = Field(default_factory=list)
    items: List[ReportItem] = Field(default_factory=list)


class ItemEnrichment(BaseModel):
    summary_zh: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    action_suggestion: str = Field(min_length=1)
    detail_zh: str = Field(min_length=1)


class CodexReportDraft(BaseModel):
    executive_summary: str = Field(min_length=1)
    recommendations: List[str] = Field(min_length=1)
    item_enrichments: Dict[str, ItemEnrichment]


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
