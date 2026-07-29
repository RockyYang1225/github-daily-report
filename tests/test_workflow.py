from pathlib import Path

import yaml


def test_daily_report_workflow_is_manual_only():
    workflow_text = Path(".github/workflows/daily-report.yml").read_text(encoding="utf-8")
    workflow = yaml.load(workflow_text, Loader=yaml.BaseLoader)

    assert set(workflow["on"]) == {"workflow_dispatch"}
