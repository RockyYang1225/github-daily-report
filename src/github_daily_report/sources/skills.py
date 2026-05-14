from __future__ import annotations

from datetime import datetime, timezone

from github_daily_report.models import ReportItem, SourceResult


class SkillsSource:
    name = "Skills and Agent Tools"

    def fetch(self) -> SourceResult:
        return SourceResult(
            source=self.name,
            items=[
                ReportItem(
                    title="Agent skills and MCP tools",
                    url="https://github.com/search?q=agent+skills+MCP&type=repositories",
                    source=self.name,
                    category="skills",
                    summary="Discovery query for practical agent skills and MCP tooling.",
                    published_at=datetime.now(timezone.utc),
                    tags=["skills", "agents", "mcp"],
                    score_signals={"source": 1.0},
                )
            ],
        )
