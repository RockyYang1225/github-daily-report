from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from github_daily_report.codex_pipeline import CandidateBatch, CodexReportDraft, current_report_date


def test_current_report_date_uses_configured_timezone():
    now = datetime(2026, 7, 28, 23, 30, tzinfo=timezone.utc)

    assert current_report_date("Asia/Shanghai", now=now).isoformat() == "2026-07-29"


def test_codex_draft_requires_non_empty_editorial_fields():
    with pytest.raises(ValidationError):
        CodexReportDraft.model_validate(
            {"executive_summary": "", "recommendations": [], "item_enrichments": {}}
        )


def test_candidate_batch_serializes_report_items(sample_items):
    batch = CandidateBatch(
        report_date="2026-07-29",
        timezone="Asia/Shanghai",
        source_warnings=[],
        items=sample_items,
    )

    restored = CandidateBatch.model_validate_json(batch.model_dump_json())

    assert restored.items[0].url == sample_items[0].url
