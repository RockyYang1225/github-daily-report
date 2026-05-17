from __future__ import annotations

from typing import List

from github_daily_report.models import SourceResult
from github_daily_report.sources.github import GitHubSearchSource


class SkillsSource:
    name = "Skills and Agent Tools"

    def __init__(self, queries: List[str] = None, limit: int = 5):
        self.queries = queries or [
            "agent skills MCP",
            "Claude Code agent",
            "OpenAI Agents SDK",
            "browser-use automation",
        ]
        self.limit = limit

    def fetch(self) -> SourceResult:
        items = []
        warnings = []
        for query in self.queries:
            result = GitHubSearchSource(query, limit=self.limit, source_name=f"{self.name}: {query}").fetch()
            warnings.extend(result.warnings)
            for item in result.items:
                item.category = "skills"
                item.source = self.name
                item.tags = sorted(set(item.tags + ["skills", "agents"]))
                items.append(item)
        return SourceResult(source=self.name, items=items[: self.limit], warnings=warnings)
