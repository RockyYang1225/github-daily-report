from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from github_daily_report.models import ReportItem, SourceResult


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_github_search(data: Dict[str, Any], source_name: str) -> List[ReportItem]:
    items: List[ReportItem] = []
    for entry in data.get("items", []):
        items.append(
            ReportItem(
                title=entry.get("full_name", entry.get("name", "Untitled repository")),
                url=entry.get("html_url", ""),
                source=source_name,
                category="github",
                summary=entry.get("description") or "",
                published_at=_parse_datetime(entry.get("updated_at")),
                tags=entry.get("topics") or [],
                score_signals={"stars": float(entry.get("stargazers_count") or 0)},
            )
        )
    return items


class GitHubSearchSource:
    def __init__(self, query: str, limit: int = 5, source_name: str = "GitHub AI Search"):
        self.query = query
        self.limit = limit
        self.name = source_name

    def fetch(self) -> SourceResult:
        try:
            response = httpx.get(
                "https://api.github.com/search/repositories",
                params={"q": self.query, "sort": "stars", "order": "desc", "per_page": self.limit},
                timeout=20.0,
            )
            response.raise_for_status()
            return SourceResult(source=self.name, items=parse_github_search(response.json(), self.name))
        except Exception as exc:
            return SourceResult(source=self.name, warnings=[f"{self.name} failed: {exc}"], error=str(exc))


def fixture_items() -> List[ReportItem]:
    return [
        ReportItem(
            title="acme/agent-kit",
            url="https://github.com/acme/agent-kit",
            source="GitHub Fixture",
            category="github",
            summary="Toolkit for building AI agents",
            published_at=datetime.now(timezone.utc),
            tags=["ai", "agents"],
            score_signals={"stars": 1234},
        )
    ]
