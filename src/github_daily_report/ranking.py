from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse

from github_daily_report.models import ReportItem


def normalize_item_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def _dedupe_key(item: ReportItem) -> str:
    if item.url:
        return normalize_item_url(item.url)
    return item.title.strip().lower()


def deduplicate_items(items: Iterable[ReportItem]) -> List[ReportItem]:
    chosen: Dict[str, ReportItem] = {}
    for item in items:
        key = _dedupe_key(item)
        current = chosen.get(key)
        if current is None or item.score > current.score:
            chosen[key] = item
    return sorted(chosen.values(), key=lambda entry: entry.score, reverse=True)


def _split_seen_items(items: List[ReportItem], seen_urls: Optional[Set[str]]) -> Tuple[List[ReportItem], List[ReportItem]]:
    if not seen_urls:
        return items, []
    normalized_seen = {normalize_item_url(url) for url in seen_urls}
    unseen: List[ReportItem] = []
    seen: List[ReportItem] = []
    for item in items:
        if normalize_item_url(item.url) in normalized_seen:
            seen.append(item)
        else:
            unseen.append(item)
    return unseen, seen


def rank_items(
    items: Iterable[ReportItem],
    final_limit: int,
    seen_urls: Optional[Set[str]] = None,
) -> List[ReportItem]:
    unique_items = deduplicate_items(items)
    unseen_items, seen_items = _split_seen_items(unique_items, seen_urls)
    pool = unseen_items if len(unseen_items) >= final_limit else unseen_items + seen_items
    by_category: Dict[str, List[ReportItem]] = {}
    for item in pool:
        by_category.setdefault(item.category, []).append(item)

    selected: List[ReportItem] = []
    used_urls = set()
    categories = sorted(by_category, key=lambda category: by_category[category][0].score, reverse=True)
    for category in categories:
        candidate = by_category[category][0]
        selected.append(candidate)
        used_urls.add(normalize_item_url(candidate.url))
        if len(selected) >= final_limit:
            return selected

    for item in pool:
        key = normalize_item_url(item.url)
        if key in used_urls:
            continue
        selected.append(item)
        used_urls.add(key)
        if len(selected) >= final_limit:
            break

    return selected
