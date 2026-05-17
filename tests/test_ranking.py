from datetime import datetime, timezone

from github_daily_report.models import ReportItem
from github_daily_report.ranking import deduplicate_items, rank_items


def item(title, url, category, score=0.0):
    return ReportItem(
        title=title,
        url=url,
        source="fixture",
        category=category,
        summary="short",
        published_at=datetime(2026, 5, 14, tzinfo=timezone.utc),
        tags=["AI"],
        score_signals={"stars": score},
    )


def test_deduplicate_items_prefers_higher_signal_duplicate_url():
    low = item("Tool", "https://github.com/acme/tool", "github", 10)
    high = item("Tool updated", "https://github.com/acme/tool", "github", 50)

    result = deduplicate_items([low, high])

    assert result == [high]


def test_rank_items_preserves_category_diversity():
    ranked = rank_items(
        [
            item("Repo 1", "https://example.com/1", "github", 100),
            item("Repo 2", "https://example.com/2", "github", 90),
            item("Paper", "https://example.com/3", "papers", 40),
            item("Model", "https://example.com/4", "models", 35),
        ],
        final_limit=3,
    )

    assert [entry.category for entry in ranked] == ["github", "papers", "models"]


def test_rank_items_prefers_unseen_urls_before_recently_seen():
    seen = item("Seen Repo", "https://github.com/acme/seen", "github", 100)
    unseen = item("Fresh Repo", "https://github.com/acme/fresh", "github", 10)

    ranked = rank_items([seen, unseen], final_limit=1, seen_urls={"https://github.com/acme/seen"})

    assert ranked == [unseen]
