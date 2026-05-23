from __future__ import annotations

import json
import re
from typing import Iterable, List

import httpx

from github_daily_report.models import ReportContent, ReportItem
from github_daily_report.ranking import normalize_item_url


class SummarizerError(RuntimeError):
    """Raised when the LLM cannot produce valid report content."""


DEFAULT_SECTION_LIMIT = 5
TODAY_HIGHLIGHTS_LIMIT = 10


class OpenRouterSummarizer:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def summarize(self, items: Iterable[ReportItem]) -> ReportContent:
        original_items = list(items)
        item_payload = [
            {
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "category": item.category,
                "summary": item.summary,
                "tags": item.tags,
            }
            for item in original_items
        ]
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/RockyYang1225/github-daily-report",
                "X-Title": "GitHub Daily Report",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是 AI 开发者日报编辑。请只返回严格 JSON，包含 "
                            "executive_summary、recommendations、item_enrichments。"
                            "item_enrichments 必须覆盖用户输入里的每一个 URL，并以原始 URL 为 key。"
                            "每项必须包含中文 summary_zh、why_it_matters、action_suggestion、detail_zh。"
                            "summary_zh 必须是中文项目介绍，不要照抄英文描述。"
                            "detail_zh 要更详细，说明项目用途、适合人群、可尝试的场景。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(item_payload, ensure_ascii=False),
                    },
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=60.0,
        )
        try:
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = _parse_json_content(content)
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
            raise SummarizerError(f"OpenRouter summarization failed: {exc}") from exc

        enriched_items = _apply_item_enrichments(original_items, parsed.get("item_enrichments", {}))
        return ReportContent(
            executive_summary=parsed.get("executive_summary", ""),
            sections=_group_items(enriched_items),
            recommendations=_normalize_recommendations(parsed.get("recommendations", [])),
        )


def _group_items(items: Iterable[ReportItem]) -> dict:
    grouped: dict = {}
    item_list = list(items)
    for item in item_list:
        section = {
            "github": "GitHub 热门项目",
            "models": "模型与数据集",
            "papers": "论文与代码",
            "developer-news": "AI 开发者资讯",
            "skills": "Skills / Agents / 工具动态",
        }.get(item.category, "今日必看")
        section_items = grouped.setdefault(section, [])
        if len(section_items) < DEFAULT_SECTION_LIMIT:
            section_items.append(item)
    grouped["今日必看"] = item_list[:TODAY_HIGHLIGHTS_LIMIT]
    return grouped


def _parse_json_content(content: str) -> dict:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    if not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            stripped = stripped[start : end + 1]
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise json.JSONDecodeError("Expected JSON object", stripped, 0)
    return parsed


def _normalize_recommendations(raw_recommendations) -> List[str]:
    if not isinstance(raw_recommendations, list):
        return []

    normalized: List[str] = []
    for entry in raw_recommendations:
        if isinstance(entry, str):
            text = entry.strip()
        elif isinstance(entry, dict):
            priority = str(entry.get("priority", "")).strip()
            action = str(entry.get("action", entry.get("title", ""))).strip()
            reason = str(entry.get("reason", entry.get("why", ""))).strip()
            head = f"{priority}：{action}" if priority and action else action or priority
            if head and reason:
                text = f"{head}。{reason}"
            else:
                text = head or reason
        else:
            text = str(entry).strip()
        if text:
            normalized.append(text)
    return normalized


def _apply_item_enrichments(items: List[ReportItem], raw_enrichments) -> List[ReportItem]:
    if not isinstance(raw_enrichments, dict):
        return items
    enrichments = {normalize_item_url(url): value for url, value in raw_enrichments.items() if isinstance(value, dict)}
    enriched_items: List[ReportItem] = []
    for item in items:
        enrichment = enrichments.get(normalize_item_url(item.url))
        if not enrichment:
            enriched_items.append(item)
            continue
        enriched_items.append(
            item.model_copy(
                update={
                    "summary_zh": _clean_optional_text(enrichment.get("summary_zh")),
                    "why_it_matters": _clean_optional_text(enrichment.get("why_it_matters")),
                    "action_suggestion": _clean_optional_text(enrichment.get("action_suggestion")),
                    "detail_zh": _clean_optional_text(enrichment.get("detail_zh")),
                }
            )
        )
    return enriched_items


def _clean_optional_text(value) -> str:
    return str(value).strip() if value else None


class FixtureSummarizer:
    def summarize(self, items: Iterable[ReportItem]) -> ReportContent:
        item_list = list(items)
        grouped = _group_items(item_list)
        return ReportContent(
            executive_summary="今天的 AI 开发者日报已生成，重点关注项目、模型、论文和工具动态。",
            sections=grouped,
            recommendations=["挑一个 GitHub 项目快速试用。", "收藏一篇论文或教程。", "检查是否有适合自动化工作流的新工具。"],
        )


class FallbackSummarizer:
    def summarize(self, items: Iterable[ReportItem]) -> ReportContent:
        item_list = list(items)
        grouped = _group_items(item_list)
        return ReportContent(
            executive_summary=(
                "今天的 AI 开发者日报以基础版生成：AI 总结服务暂时不可用，"
                "以下内容按抓取来源和排序信号直接整理。"
            ),
            sections=grouped,
            recommendations=[
                "优先查看「今日必看」中的前 3 个条目，判断是否值得深入试用。",
                "打开项目原始链接确认 README、更新频率和使用方式。",
                "如果今天的基础版信息偏粗略，可以稍后重新触发 workflow 获取 AI 总结版。",
            ],
        )
