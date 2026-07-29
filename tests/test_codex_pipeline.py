from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from github_daily_report.codex_pipeline import (
    CandidateBatch,
    CodexReportDraft,
    build_codex_report,
    current_report_date,
)


def _draft_payload(items):
    return {
        "executive_summary": "今天重点关注 Agent 工具与模型工程。",
        "recommendations": ["选择一个工具完成最小验证。"],
        "item_enrichments": {
            item.url: {
                "summary_zh": f"{item.title} 的中文介绍。",
                "why_it_matters": "它能缩短验证路径。",
                "action_suggestion": "阅读文档并运行示例。",
                "detail_zh": "适合需要快速验证相关能力的开发者。",
            }
            for item in items
        },
    }


def _complete_draft(items):
    return CodexReportDraft.model_validate(_draft_payload(items))


def test_current_report_date_uses_configured_timezone():
    now = datetime(2026, 7, 28, 23, 30, tzinfo=timezone.utc)

    assert current_report_date("Asia/Shanghai", now=now).isoformat() == "2026-07-29"


def test_codex_draft_requires_non_empty_editorial_fields():
    with pytest.raises(ValidationError):
        CodexReportDraft.model_validate(
            {"executive_summary": "", "recommendations": [], "item_enrichments": {}}
        )


def test_codex_draft_rejects_whitespace_only_editorial_fields(sample_items):
    payload = _draft_payload(sample_items)
    payload["executive_summary"] = "   "

    with pytest.raises(ValidationError):
        CodexReportDraft.model_validate(payload)


def test_codex_draft_rejects_english_only_editorial_fields(sample_items):
    payload = _draft_payload(sample_items)
    payload["item_enrichments"][sample_items[0].url]["summary_zh"] = "English only summary"

    with pytest.raises(ValidationError, match="Chinese text"):
        CodexReportDraft.model_validate(payload)


def test_candidate_batch_serializes_report_items(sample_items):
    batch = CandidateBatch(
        report_date="2026-07-29",
        timezone="Asia/Shanghai",
        source_warnings=[],
        items=sample_items,
    )

    restored = CandidateBatch.model_validate_json(batch.model_dump_json())

    assert restored.items[0].url == sample_items[0].url


def test_build_codex_report_renders_markdown_and_html(sample_items):
    batch = CandidateBatch(
        report_date="2026-07-29",
        timezone="Asia/Shanghai",
        items=sample_items,
    )

    report = build_codex_report(batch, _complete_draft(sample_items))

    assert "# AI 开发者日报 - 2026-07-29" in report.markdown
    assert "<html" in report.html
    assert "中文介绍" in report.markdown


def test_build_codex_report_rejects_missing_item_enrichment(sample_items):
    draft = _complete_draft(sample_items)
    draft.item_enrichments.pop(sample_items[-1].url)
    batch = CandidateBatch(
        report_date="2026-07-29",
        timezone="Asia/Shanghai",
        items=sample_items,
    )

    with pytest.raises(ValueError, match="Missing Codex enrichment"):
        build_codex_report(batch, draft)
