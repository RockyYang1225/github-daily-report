from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from github_daily_report.models import ReportItem


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
