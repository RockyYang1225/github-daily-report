from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import List

import httpx

from github_daily_report.models import ReportItem, SourceResult
from github_daily_report.sources.github import GitHubSearchSource


SKILLS_DIRECTORY_URL = "https://www.skills.sh/"
SKILL_ENTRY_RE = re.compile(
    r'\{"source":"(?P<source>[^"]+)",'
    r'"skillId":"(?P<skill_id>[^"]+)",'
    r'"name":"(?P<name>[^"]+)",'
    r'"installs":(?P<installs>\d+),'
    r'"weeklyInstalls":\[(?P<weekly_installs>[^\]]*)\]'
    r'(?:,"isOfficial":(?P<is_official>true|false))?'
)


def _parse_weekly_installs(value: str) -> float:
    installs = []
    for entry in value.split(","):
        entry = entry.strip()
        if entry.isdigit():
            installs.append(float(entry))
    return sum(installs)


def parse_skills_directory(html: str, limit: int = 10) -> List[ReportItem]:
    decoded = html.replace(r"\"", '"')
    items: List[ReportItem] = []
    for match in SKILL_ENTRY_RE.finditer(decoded):
        source = match.group("source")
        skill_id = match.group("skill_id")
        name = match.group("name")
        installs = float(match.group("installs"))
        weekly_installs = _parse_weekly_installs(match.group("weekly_installs"))
        is_official = match.group("is_official") == "true"
        tags = ["skills.sh"]
        if is_official:
            tags.append("official")
        summary_parts = [
            f"Agent skill from {source}",
            f"{int(installs):,} installs",
            f"{int(weekly_installs):,} recent installs",
        ]
        if is_official:
            summary_parts.append("official listing")
        items.append(
            ReportItem(
                title=f"{source}/{skill_id}",
                url=f"https://www.skills.sh/{source}/{skill_id}",
                source="skills.sh",
                category="skills",
                summary="; ".join(summary_parts) + ".",
                published_at=datetime.now(timezone.utc),
                tags=tags,
                score_signals={"installs": installs, "weekly_installs": weekly_installs},
                metadata={"skill_id": skill_id, "name": name, "directory_source": source},
            )
        )
        if len(items) >= limit:
            break
    return items


class SkillsDirectorySource:
    name = "skills.sh"

    def __init__(self, limit: int = 10):
        self.limit = limit

    def fetch(self) -> SourceResult:
        try:
            response = httpx.get(
                SKILLS_DIRECTORY_URL,
                timeout=20.0,
                headers={"User-Agent": "github-daily-report"},
            )
            response.raise_for_status()
            return SourceResult(source=self.name, items=parse_skills_directory(response.text, limit=self.limit))
        except Exception as exc:
            return SourceResult(source=self.name, warnings=[f"{self.name} failed: {exc}"], error=str(exc))


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
