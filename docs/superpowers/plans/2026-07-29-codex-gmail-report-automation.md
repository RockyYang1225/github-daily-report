# Codex Gmail Report Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the scheduled OpenRouter/SMTP report path with a Codex desktop automation that generates an enriched report, sends it through Gmail, and archives it to the remote repository every Monday and Wednesday at 07:00 Asia/Shanghai.

**Architecture:** Add a Codex-facing pipeline with two deterministic CLI commands: `collect` exports ranked candidates without secret environment variables, and `render-codex` validates Codex enrichment JSON and renders Markdown plus HTML. A versioned runbook defines duplicate detection, Gmail delivery, and Git archiving; the Codex scheduled task follows that runbook while the GitHub Actions workflow remains manual-only.

**Tech Stack:** Python 3.11, Typer, Pydantic v2, `zoneinfo`, pytest, GitHub Actions, Codex Scheduled tasks, Gmail plugin.

---

## File Map

- Create `src/github_daily_report/codex_pipeline.py`: timezone-aware report date, candidate batch schema, Codex draft schema, validation, and report construction.
- Create `src/github_daily_report/__main__.py`: stable `python -m github_daily_report` entry point for unattended runs.
- Modify `src/github_daily_report/summarizer.py`: expose the existing enrichment-to-content conversion as a reusable public function.
- Modify `src/github_daily_report/cli.py`: add `collect` and `render-codex`, and use the configured timezone in legacy commands.
- Create `tests/test_codex_pipeline.py`: unit coverage for timezone, complete enrichment, missing enrichment, and rendering.
- Modify `tests/test_cli.py`: CLI coverage proving the Codex path needs neither OpenRouter nor SMTP settings.
- Create `tests/test_workflow.py`: enforce manual-only GitHub Actions behavior.
- Modify `.github/workflows/daily-report.yml`: remove the scheduled trigger while preserving `workflow_dispatch`.
- Create `docs/codex-automation-runbook.md`: durable Gmail task procedure and exact recipients.
- Modify `README.md`: document the Codex/Gmail primary path and GitHub Actions fallback.

### Task 1: Add timezone-aware Codex pipeline models

**Files:**
- Create: `src/github_daily_report/codex_pipeline.py`
- Test: `tests/test_codex_pipeline.py`

- [ ] **Step 1: Write failing timezone and schema tests**

```python
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from github_daily_report.codex_pipeline import (
    CandidateBatch,
    CodexReportDraft,
    current_report_date,
)
from github_daily_report.models import ReportItem


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
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_codex_pipeline.py -v`

Expected: collection fails because `github_daily_report.codex_pipeline` does not exist.

- [ ] **Step 3: Implement the models and timezone helper**

```python
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from github_daily_report.models import ReportItem


class CandidateBatch(BaseModel):
    report_date: date
    timezone: str
    source_warnings: List[str] = Field(default_factory=list)
    items: List[ReportItem] = Field(default_factory=list)


class ItemEnrichment(BaseModel):
    summary_zh: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    action_suggestion: str = Field(min_length=1)
    detail_zh: str = Field(min_length=1)


class CodexReportDraft(BaseModel):
    executive_summary: str = Field(min_length=1)
    recommendations: List[str] = Field(min_length=1)
    item_enrichments: Dict[str, ItemEnrichment]


def current_report_date(timezone_name: str, now: Optional[datetime] = None) -> date:
    current = now or datetime.now(tz=ZoneInfo("UTC"))
    return current.astimezone(ZoneInfo(timezone_name)).date()
```

- [ ] **Step 4: Run the focused tests**

Run: `.venv/bin/python -m pytest tests/test_codex_pipeline.py -v`

Expected: three tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/github_daily_report/codex_pipeline.py tests/test_codex_pipeline.py
git commit -m "feat: add Codex report pipeline models"
```

### Task 2: Export ranked candidates without AI or mail credentials

**Files:**
- Modify: `src/github_daily_report/codex_pipeline.py`
- Modify: `src/github_daily_report/cli.py`
- Create: `src/github_daily_report/__main__.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write a failing CLI test**

```python
import json


def test_collect_exports_candidates_without_secret_env(tmp_path, monkeypatch):
    config_path = write_test_config(tmp_path)
    output_path = tmp_path / "candidates.json"
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    result = CliRunner().invoke(
        app,
        [
            "collect",
            "--config",
            str(config_path),
            "--reports-dir",
            str(tmp_path / "reports"),
            "--output",
            str(output_path),
            "--use-fixtures",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["timezone"] == "Asia/Shanghai"
    assert payload["items"]
```

Extract the repeated test YAML creation into `write_test_config(tmp_path)` so existing tests reuse the same valid config without changing their assertions.

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `.venv/bin/python -m pytest tests/test_cli.py::test_collect_exports_candidates_without_secret_env -v`

Expected: Typer reports that command `collect` does not exist.

- [ ] **Step 3: Add candidate batch construction**

```python
def build_candidate_batch(
    results: List[SourceResult],
    reports_dir: Path,
    report_date: date,
    timezone_name: str,
    lookback_days: int,
    final_items: int,
) -> CandidateBatch:
    warnings = [warning for result in results for warning in result.warnings]
    items = [item for result in results for item in result.items]
    seen = load_seen_urls(reports_dir, today=report_date, lookback_days=lookback_days)
    warnings.extend(seen.warnings)
    ranked = rank_items(items, final_items, seen_urls=seen.urls)
    return CandidateBatch(
        report_date=report_date,
        timezone=timezone_name,
        source_warnings=warnings,
        items=ranked,
    )
```

Import `Path`, `SourceResult`, `load_seen_urls`, and `rank_items` in `codex_pipeline.py`.

- [ ] **Step 4: Add the `collect` command**

```python
@app.command("collect")
def collect(
    config: Path = typer.Option(Path("config/sources.yml"), "--config"),
    reports_dir: Path = typer.Option(Path("reports"), "--reports-dir"),
    output: Path = typer.Option(Path("/tmp/github-daily-report-candidates.json"), "--output"),
    use_fixtures: bool = typer.Option(False, "--use-fixtures"),
):
    public_config = load_public_config(config)
    results = _collect_fixture_results() if use_fixtures else _collect_live_results(public_config)
    batch = build_candidate_batch(
        results=results,
        reports_dir=reports_dir,
        report_date=current_report_date(public_config.report.timezone),
        timezone_name=public_config.report.timezone,
        lookback_days=public_config.history.lookback_days,
        final_items=public_config.limits.final_items,
    )
    if not batch.items:
        typer.echo("No report candidates were collected.", err=True)
        raise typer.Exit(1)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(batch.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Candidates written: {output}")
```

- [ ] **Step 5: Use the configured timezone in the legacy report path**

In `_build_report`, replace both `date.today()` calls with one value:

```python
report_date = current_report_date(public_config.report.timezone)
seen = load_seen_urls(output_dir, today=report_date, lookback_days=public_config.history.lookback_days)
# ...
report = DailyReport(report_date=report_date, content=content, source_warnings=warnings)
```

- [ ] **Step 6: Add a stable module entry point**

```python
from github_daily_report.cli import app


if __name__ == "__main__":
    app()
```

Verify the command surface with:

Run: `.venv/bin/python -m github_daily_report --help`

Expected: Typer lists `collect`, `dry-run`, and `run`.

- [ ] **Step 7: Run CLI tests**

Run: `.venv/bin/python -m pytest tests/test_cli.py -v`

Expected: all CLI tests pass without requiring secrets for `collect`.

- [ ] **Step 8: Commit Task 2**

```bash
git add src/github_daily_report/codex_pipeline.py src/github_daily_report/cli.py src/github_daily_report/__main__.py tests/test_cli.py
git commit -m "feat: export report candidates for Codex"
```

### Task 3: Validate Codex enrichment and render email artifacts

**Files:**
- Modify: `src/github_daily_report/summarizer.py`
- Modify: `src/github_daily_report/codex_pipeline.py`
- Modify: `src/github_daily_report/cli.py`
- Modify: `tests/test_codex_pipeline.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing report construction tests**

```python
def complete_draft(items):
    return CodexReportDraft(
        executive_summary="今天重点关注 Agent 工具与模型工程。",
        recommendations=["选择一个工具完成最小验证。"],
        item_enrichments={
            item.url: {
                "summary_zh": f"{item.title} 的中文介绍。",
                "why_it_matters": "它能缩短验证路径。",
                "action_suggestion": "阅读文档并运行示例。",
                "detail_zh": "适合需要快速验证相关能力的开发者。",
            }
            for item in items
        },
    )


def test_build_codex_report_renders_markdown_and_html(sample_items):
    batch = CandidateBatch(
        report_date="2026-07-29",
        timezone="Asia/Shanghai",
        items=sample_items,
    )
    report = build_codex_report(batch, complete_draft(sample_items))
    assert "# AI 开发者日报 - 2026-07-29" in report.markdown
    assert "<html" in report.html
    assert "中文介绍" in report.markdown


def test_build_codex_report_rejects_missing_item_enrichment(sample_items):
    draft = complete_draft(sample_items)
    draft.item_enrichments.pop(sample_items[-1].url)
    batch = CandidateBatch(
        report_date="2026-07-29",
        timezone="Asia/Shanghai",
        items=sample_items,
    )
    with pytest.raises(ValueError, match="Missing Codex enrichment"):
        build_codex_report(batch, draft)
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_codex_pipeline.py -v`

Expected: import fails because `build_codex_report` is not defined.

- [ ] **Step 3: Expose reusable enrichment conversion**

In `summarizer.py`, add and use:

```python
def build_report_content(items: Iterable[ReportItem], parsed: dict) -> ReportContent:
    original_items = list(items)
    enriched_items = _apply_item_enrichments(original_items, parsed.get("item_enrichments", {}))
    return ReportContent(
        executive_summary=str(parsed.get("executive_summary", "")).strip(),
        sections=_group_items(enriched_items),
        recommendations=_normalize_recommendations(parsed.get("recommendations", [])),
    )
```

Replace the matching block in `OpenRouterSummarizer.summarize` with `return build_report_content(original_items, parsed)`.

- [ ] **Step 4: Implement complete-coverage validation and rendering**

```python
def build_codex_report(batch: CandidateBatch, draft: CodexReportDraft) -> DailyReport:
    candidate_urls = {normalize_item_url(item.url) for item in batch.items}
    enrichment_urls = {normalize_item_url(url) for url in draft.item_enrichments}
    missing = sorted(candidate_urls - enrichment_urls)
    if missing:
        raise ValueError(f"Missing Codex enrichment for: {', '.join(missing)}")

    content = build_report_content(batch.items, draft.model_dump())
    report = DailyReport(
        report_date=batch.report_date,
        content=content,
        source_warnings=batch.source_warnings,
    )
    report.markdown = render_markdown(report)
    report.html = render_html(report)
    return report
```

- [ ] **Step 5: Write the failing `render-codex` CLI test**

The test writes a `CandidateBatch` and complete `CodexReportDraft` to temporary JSON files, invokes:

```python
result = CliRunner().invoke(
    app,
    [
        "render-codex",
        "--candidates",
        str(candidates_path),
        "--draft",
        str(draft_path),
        "--output-dir",
        str(tmp_path / "reports"),
        "--html-output",
        str(tmp_path / "report.html"),
    ],
)
```

Assert exit code `0`, one Markdown report exists, and `report.html` contains `<html`.

- [ ] **Step 6: Add `render-codex`**

```python
@app.command("render-codex")
def render_codex(
    candidates: Path = typer.Option(..., "--candidates", exists=True, readable=True),
    draft: Path = typer.Option(..., "--draft", exists=True, readable=True),
    output_dir: Path = typer.Option(Path("reports"), "--output-dir"),
    html_output: Path = typer.Option(Path("/tmp/github-daily-report.html"), "--html-output"),
):
    batch = CandidateBatch.model_validate_json(candidates.read_text(encoding="utf-8"))
    codex_draft = CodexReportDraft.model_validate_json(draft.read_text(encoding="utf-8"))
    report = build_codex_report(batch, codex_draft)
    markdown_path = _write_report(report, output_dir)
    html_output.parent.mkdir(parents=True, exist_ok=True)
    html_output.write_text(report.html, encoding="utf-8")
    typer.echo(f"Report written: {markdown_path}")
    typer.echo(f"Email HTML written: {html_output}")
```

- [ ] **Step 7: Run focused and full tests**

Run: `.venv/bin/python -m pytest tests/test_codex_pipeline.py tests/test_cli.py tests/test_summarizer.py -v`

Expected: all focused tests pass.

Run: `.venv/bin/python -m pytest -v`

Expected: full suite passes.

- [ ] **Step 8: Commit Task 3**

```bash
git add src/github_daily_report/codex_pipeline.py src/github_daily_report/summarizer.py src/github_daily_report/cli.py tests/test_codex_pipeline.py tests/test_cli.py tests/test_summarizer.py
git commit -m "feat: render Codex-enriched reports"
```

### Task 4: Make GitHub Actions manual-only

**Files:**
- Modify: `.github/workflows/daily-report.yml`
- Create: `tests/test_workflow.py`

- [ ] **Step 1: Write the failing workflow test**

```python
from pathlib import Path


def test_daily_report_workflow_is_manual_only():
    workflow = Path(".github/workflows/daily-report.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "cron:" not in workflow
```

- [ ] **Step 2: Run the workflow test and verify it fails**

Run: `.venv/bin/python -m pytest tests/test_workflow.py -v`

Expected: failure because the workflow still contains `schedule:` and `cron:`.

- [ ] **Step 3: Remove only the scheduled trigger**

The workflow header becomes:

```yaml
name: Daily AI Developer Report

on:
  workflow_dispatch:
```

Keep all existing manual workflow steps unchanged as the emergency fallback.

- [ ] **Step 4: Run the workflow and full test suites**

Run: `.venv/bin/python -m pytest tests/test_workflow.py -v`

Expected: pass.

Run: `.venv/bin/python -m pytest -v`

Expected: full suite passes.

- [ ] **Step 5: Commit Task 4**

```bash
git add .github/workflows/daily-report.yml tests/test_workflow.py
git commit -m "chore: make legacy report workflow manual only"
```

### Task 5: Version the Codex/Gmail operating procedure

**Files:**
- Create: `docs/codex-automation-runbook.md`
- Modify: `README.md`

- [ ] **Step 1: Write the runbook**

The runbook must contain these exact operational requirements:

```markdown
# Codex Gmail Report Runbook

1. Compute today's date in `Asia/Shanghai` as `YYYY-MM-DD`.
2. Use `$gmail:gmail` to search sent mail for the exact subject `AI 开发者日报 - YYYY-MM-DD`.
3. If a matching message was already sent to both configured recipients, stop without sending.
4. Run `git pull --ff-only origin main`; stop on failure and do not modify unrelated files.
5. Run `.venv/bin/python -m github_daily_report collect --config config/sources.yml --reports-dir reports --output /tmp/github-daily-report-candidates.json`.
6. Read the candidate JSON and create `/tmp/github-daily-report-draft.json` with `executive_summary`, at least one `recommendations` entry, and complete `item_enrichments` for every candidate URL.
7. Run `.venv/bin/python -m github_daily_report render-codex --candidates /tmp/github-daily-report-candidates.json --draft /tmp/github-daily-report-draft.json --output-dir reports --html-output /tmp/github-daily-report.html`.
8. Send the HTML through Gmail from the authenticated account to `rockyyang951225@gmail.com, zoeyli1997@gmail.com` with the exact subject.
9. Stage only `reports/YYYY-MM-DD.md`, commit with `chore: archive daily report`, and push `main`.
10. Report Gmail message id and Git commit id. If sending succeeds but Git fails, state that explicitly and do not resend.
```

Also specify the editorial JSON field requirements and the rule against invented claims.

- [ ] **Step 2: Update README**

Describe Codex Scheduled + Gmail as the primary path, document `collect` and `render-codex`, state the Monday/Wednesday 07:00 Asia/Shanghai schedule, explain that the computer and Codex App must be running, and label GitHub Actions as manual fallback only.

- [ ] **Step 3: Verify documentation against the design**

Run: `rg -n "OpenRouter|Gmail|workflow_dispatch|Asia/Shanghai|07:00|rockyyang951225|zoeyli1997|render-codex|collect" README.md docs/codex-automation-runbook.md`

Expected: every operational dependency, schedule, recipient, and command is present; no daily GitHub Actions schedule is described.

- [ ] **Step 4: Commit Task 5**

```bash
git add README.md docs/codex-automation-runbook.md
git commit -m "docs: add Codex Gmail report runbook"
```

### Task 6: Verify, deploy, and create the scheduled task

**Files:**
- No additional source files expected.

- [ ] **Step 1: Run final local verification**

Run: `.venv/bin/python -m pytest -v`

Expected: all tests pass.

Run fixture pipeline without secrets:

```bash
env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL -u SMTP_PASSWORD \
  .venv/bin/python -m github_daily_report collect \
  --config config/sources.yml \
  --reports-dir reports \
  --output /tmp/github-daily-report-fixture-candidates.json \
  --use-fixtures
```

Expected: candidate JSON is written and contains items.

- [ ] **Step 2: Fast-forward local main and push**

Merge the implementation branch into local `main` with `git merge --ff-only`, then run `git push origin main`. Do not stage or commit `.DS_Store`, `docs/knowledge/`, or `docs/resume-project-guide.md`.

Expected: `origin/main` contains the design, plan, implementation, docs, and manual-only workflow.

- [ ] **Step 3: Run one live Codex/Gmail report manually**

Follow `docs/codex-automation-runbook.md` using the connected Gmail plugin. The live run must use the exact recipients and subject date in `Asia/Shanghai`. This is an explicitly authorized send, not a draft.

Expected: Gmail returns a sent message id, both recipients are present, and `reports/YYYY-MM-DD.md` is committed and pushed.

- [ ] **Step 4: Verify idempotency**

Search Gmail again for the exact subject and inspect recipients. Simulate the runbook preflight and confirm it stops before collection or send when both recipients already received the report.

Expected: one sent message for the correct Beijing date and no duplicate send.

- [ ] **Step 5: Create the active Codex scheduled task**

Create a local cron automation named `AI 开发者日报 Gmail` with:

- workspace: `/Users/rockyyang/Wrokspace/每日推送/github-daily-report`
- execution environment: `local`
- schedule: Monday and Wednesday at 07:00 in the user's `Asia/Shanghai` locale
- status: `ACTIVE`
- prompt:

```text
Use $gmail:gmail. Run the AI developer report workflow in this repository by reading and following docs/codex-automation-runbook.md exactly. Generate the complete Codex enrichment for every collected candidate, send the resulting HTML report to the two authorized recipients through the connected Gmail account, archive only the generated Markdown report, and report the Gmail message id plus Git commit id. Enforce the runbook's sent-mail duplicate check before sending. Never use OpenRouter or SMTP for this scheduled run.
```

- [ ] **Step 6: Inspect the saved automation**

View the automation after creation and verify its name, active status, local workspace, Monday/Wednesday cadence, Gmail prompt, and duplicate-send instruction.

Expected: one active automation exists; no duplicate automation with the same purpose exists.

- [ ] **Step 7: Final repository verification**

Run: `git status --short --branch`

Expected: `main` is synchronized with `origin/main`; only the pre-existing untracked files remain.

Run: `git log -8 --oneline --decorate`

Expected: the report archive and implementation commits are visible on local and remote `main`.
