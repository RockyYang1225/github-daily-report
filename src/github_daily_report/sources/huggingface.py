from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from github_daily_report.models import ReportItem, SourceResult


class HuggingFaceSource:
    name = "Hugging Face"

    def fetch(self) -> SourceResult:
        return SourceResult(
            source=self.name,
            items=[
                ReportItem(
                    title="Hugging Face trending models",
                    url="https://huggingface.co/models?sort=trending",
                    source=self.name,
                    category="models",
                    summary="Trending models and datasets entry point.",
                    published_at=datetime.now(timezone.utc),
                    tags=["models", "datasets"],
                    score_signals={"source": 1.0},
                )
            ],
        )
