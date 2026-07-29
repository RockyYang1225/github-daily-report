from pathlib import Path


def test_daily_report_workflow_is_manual_only():
    workflow = Path(".github/workflows/daily-report.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "cron:" not in workflow
