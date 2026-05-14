from __future__ import annotations

from datetime import datetime, timezone

from github_daily_report.models import ReportItem, SourceResult


class ArxivSource:
    name = "arXiv"

    def fetch(self) -> SourceResult:
        return SourceResult(
            source=self.name,
            items=[
                ReportItem(
                    title="Latest AI papers on arXiv",
                    url="https://arxiv.org/list/cs.AI/recent",
                    source=self.name,
                    category="papers",
                    summary="Recent AI papers from arXiv.",
                    published_at=datetime.now(timezone.utc),
                    tags=["paper", "arxiv"],
                    score_signals={"source": 1.0},
                )
            ],
        )


class PapersWithCodeSource:
    name = "Papers with Code"

    def fetch(self) -> SourceResult:
        return SourceResult(
            source=self.name,
            items=[
                ReportItem(
                    title="Trending AI papers with code",
                    url="https://paperswithcode.com/",
                    source=self.name,
                    category="papers",
                    summary="Papers paired with implementation links.",
                    published_at=datetime.now(timezone.utc),
                    tags=["paper", "code"],
                    score_signals={"source": 1.0},
                )
            ],
        )
