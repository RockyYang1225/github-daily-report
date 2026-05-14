from datetime import datetime, timezone

import pytest

from github_daily_report.models import ReportItem


@pytest.fixture
def sample_items():
    return [
        ReportItem(
            title="acme/agent-kit",
            url="https://github.com/acme/agent-kit",
            source="GitHub",
            category="github",
            summary="Agent development toolkit",
            published_at=datetime(2026, 5, 14, tzinfo=timezone.utc),
            tags=["AI", "Agent"],
            score_signals={"stars": 1234},
        ),
        ReportItem(
            title="Useful Embedding Model",
            url="https://huggingface.co/acme/embedding",
            source="Hugging Face",
            category="models",
            summary="Embedding model for retrieval",
            published_at=datetime(2026, 5, 14, tzinfo=timezone.utc),
            tags=["embedding"],
            score_signals={"likes": 42},
        ),
    ]
