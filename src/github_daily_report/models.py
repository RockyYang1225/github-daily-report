from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ReportItem(BaseModel):
    title: str
    url: str
    source: str
    category: str
    summary: str = ""
    published_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    score_signals: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, str] = Field(default_factory=dict)

    @property
    def score(self) -> float:
        signal_score = sum(float(value) for value in self.score_signals.values())
        if not self.published_at:
            return signal_score
        now = datetime.now(timezone.utc)
        published = self.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        age_days = max((now - published).days, 0)
        return signal_score + max(0.0, 30.0 - float(age_days))


class SourceResult(BaseModel):
    source: str
    items: List[ReportItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class ReportContent(BaseModel):
    executive_summary: str
    sections: Dict[str, List[ReportItem]] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)


class DailyReport(BaseModel):
    report_date: date
    content: ReportContent
    source_warnings: List[str] = Field(default_factory=list)
    markdown: str = ""
    html: str = ""

    @classmethod
    def for_test(cls, items: List[ReportItem]) -> "DailyReport":
        return cls(
            report_date=date(2026, 5, 14),
            content=ReportContent(
                executive_summary="今天值得关注三件事。",
                sections={"今日必看": items[:1], "GitHub 热门项目": items},
                recommendations=["试用第一个项目"],
            ),
            source_warnings=[],
        )
