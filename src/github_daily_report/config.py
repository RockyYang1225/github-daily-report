from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field


class ConfigError(RuntimeError):
    """Raised when required report configuration is missing or invalid."""


class ReportSettings(BaseModel):
    title: str = "AI 开发者日报"
    timezone: str = "Asia/Shanghai"
    language: str = "zh-CN"


class Limits(BaseModel):
    per_source: int = 5
    final_items: int = 20


class RssFeed(BaseModel):
    name: str
    url: str


class HistoryConfig(BaseModel):
    lookback_days: int = 14


class GitHubTrendingConfig(BaseModel):
    enabled: bool = True
    periods: List[str] = Field(default_factory=lambda: ["daily", "weekly"])
    languages: List[str] = Field(default_factory=list)


class PublicConfig(BaseModel):
    report: ReportSettings = Field(default_factory=ReportSettings)
    limits: Limits = Field(default_factory=Limits)
    history: HistoryConfig = Field(default_factory=HistoryConfig)
    github_trending: GitHubTrendingConfig = Field(default_factory=GitHubTrendingConfig)
    keywords: List[str] = Field(default_factory=list)
    rss_feeds: List[RssFeed] = Field(default_factory=list)
    news_feeds: List[RssFeed] = Field(default_factory=list)
    sources: Dict[str, bool] = Field(default_factory=dict)
    github_queries: List[str] = Field(default_factory=list)
    skills_queries: List[str] = Field(default_factory=list)
    arxiv_categories: List[str] = Field(default_factory=list)


class EnvConfig(BaseModel):
    openrouter_api_key: str
    openrouter_model: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    mail_from: Optional[str] = None
    mail_to: Optional[str] = None

    @property
    def recipients(self) -> List[str]:
        if not self.mail_to:
            return []
        return [entry.strip() for entry in self.mail_to.split(",") if entry.strip()]


def load_public_config(path: Union[str, Path]) -> PublicConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConfigError(f"Public config must be a YAML mapping: {config_path}")
    return PublicConfig.model_validate(raw)


def load_env_config(send_email: bool) -> EnvConfig:
    required = ["OPENROUTER_API_KEY", "OPENROUTER_MODEL"]
    if send_email:
        required.extend(
            [
                "SMTP_HOST",
                "SMTP_PORT",
                "SMTP_USERNAME",
                "SMTP_PASSWORD",
                "MAIL_FROM",
                "MAIL_TO",
            ]
        )

    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise ConfigError(f"Missing required configuration: {', '.join(missing)}")

    smtp_port = os.getenv("SMTP_PORT")
    return EnvConfig(
        openrouter_api_key=os.environ["OPENROUTER_API_KEY"],
        openrouter_model=os.environ["OPENROUTER_MODEL"],
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
        smtp_host=os.getenv("SMTP_HOST"),
        smtp_port=int(smtp_port) if smtp_port else None,
        smtp_username=os.getenv("SMTP_USERNAME"),
        smtp_password=os.getenv("SMTP_PASSWORD"),
        mail_from=os.getenv("MAIL_FROM"),
        mail_to=os.getenv("MAIL_TO"),
    )
