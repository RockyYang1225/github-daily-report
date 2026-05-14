from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from github_daily_report.models import SourceResult


class Source(Protocol):
    name: str

    def fetch(self) -> SourceResult:
        ...


@dataclass
class HttpSource:
    name: str
    timeout: float = 20.0
