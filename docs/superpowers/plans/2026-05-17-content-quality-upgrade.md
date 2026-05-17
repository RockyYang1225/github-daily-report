# Content Quality Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real GitHub Trending, short-term history deduplication, richer Chinese item explanations, and broader Skills/news discovery to the daily AI report.

**Architecture:** Keep the existing Python CLI pipeline and add focused modules: GitHub Trending parsing in the GitHub source, report-history URL extraction in a new history module, richer item fields in the model, enrichment normalization in the summarizer, and expanded config-driven collection in the CLI. Ranking filters recently seen URLs before final selection while preserving the existing category-diversity behavior.

**Tech Stack:** Python 3.9+, Typer, Pydantic, PyYAML, httpx, feedparser, Jinja2, pytest.

---

## File Structure

- Modify `src/github_daily_report/models.py`: add `summary_zh`, `why_it_matters`, and `action_suggestion` to `ReportItem`.
- Create `src/github_daily_report/history.py`: parse recent Markdown reports and expose normalized seen URLs.
- Modify `src/github_daily_report/ranking.py`: add URL normalization export and seen-URL filtering.
- Modify `src/github_daily_report/sources/github.py`: add GitHub Trending parser/source and reuse GitHub Search for Skills queries.
- Modify `src/github_daily_report/sources/skills.py`: collect multiple configured Skills/Agents queries instead of one static item.
- Modify `src/github_daily_report/config.py`: add history, GitHub Trending, Skills query, and news feed config fields.
- Modify `config/sources.yml`: enable Trending, history lookback, expanded Skills queries, and expanded RSS feeds.
- Modify `src/github_daily_report/summarizer.py`: enrich ranked items with Chinese explanation fields and normalize structured model output.
- Modify `src/github_daily_report/rendering.py`: render Chinese explanation and why-it-matters text per item.
- Modify `src/github_daily_report/cli.py`: collect Trending, pass history seen URLs into ranking, use expanded Skills and news config.
- Add/modify tests under `tests/`: Trending parser fixture, history parsing, ranking seen filtering, enrichment normalization, rendering output, config loading.

## Tasks

### Task 1: Model and Rendering Fields

**Files:**
- Modify: `src/github_daily_report/models.py`
- Modify: `src/github_daily_report/rendering.py`
- Test: `tests/test_rendering.py`

- [ ] Write a failing test that a rendered item includes `summary_zh` and `why_it_matters`.
- [ ] Run `pytest tests/test_rendering.py -v` and confirm the new test fails.
- [ ] Add optional `summary_zh`, `why_it_matters`, and `action_suggestion` fields to `ReportItem`.
- [ ] Update Markdown and HTML item rendering to prefer Chinese fields and show source.
- [ ] Run `pytest tests/test_rendering.py -v` and confirm it passes.

### Task 2: History Deduplication

**Files:**
- Create: `src/github_daily_report/history.py`
- Modify: `src/github_daily_report/ranking.py`
- Test: `tests/test_history.py`
- Test: `tests/test_ranking.py`

- [ ] Write failing tests for extracting Markdown links from recent reports and filtering seen URLs.
- [ ] Run `pytest tests/test_history.py tests/test_ranking.py -v` and confirm the new tests fail.
- [ ] Implement `normalize_url`, `extract_markdown_links`, `load_seen_urls`, and `filter_seen_items`.
- [ ] Update ranking to accept optional `seen_urls` and prefer unseen items, falling back to seen items only if needed.
- [ ] Run `pytest tests/test_history.py tests/test_ranking.py -v` and confirm it passes.

### Task 3: GitHub Trending Source

**Files:**
- Modify: `src/github_daily_report/sources/github.py`
- Add: `tests/fixtures/github_trending.html`
- Modify: `tests/sources/test_github_source.py`

- [ ] Write a failing parser test for a compact GitHub Trending HTML fixture.
- [ ] Run `pytest tests/sources/test_github_source.py -v` and confirm it fails.
- [ ] Implement `parse_github_trending` and `GitHubTrendingSource`.
- [ ] Run `pytest tests/sources/test_github_source.py -v` and confirm it passes.

### Task 4: Config and Collection Expansion

**Files:**
- Modify: `src/github_daily_report/config.py`
- Modify: `config/sources.yml`
- Modify: `src/github_daily_report/sources/skills.py`
- Modify: `src/github_daily_report/cli.py`
- Test: `tests/test_config.py`
- Test: `tests/test_cli.py`

- [ ] Write failing tests for loading history/trending/skills config and fixture dry-run including broader sources.
- [ ] Run `pytest tests/test_config.py tests/test_cli.py -v` and confirm new tests fail.
- [ ] Add config models for history, GitHub Trending, skills queries, and news feeds.
- [ ] Expand `config/sources.yml` with real Trending periods, Skills queries, and more RSS feeds.
- [ ] Update CLI collection to include Trending, expanded Skills queries, and history seen URLs.
- [ ] Run `pytest tests/test_config.py tests/test_cli.py -v` and confirm it passes.

### Task 5: OpenRouter Item Enrichment

**Files:**
- Modify: `src/github_daily_report/summarizer.py`
- Test: `tests/test_summarizer.py`

- [ ] Write a failing test where OpenRouter returns per-item enrichment keyed by URL.
- [ ] Run `pytest tests/test_summarizer.py -v` and confirm the new test fails.
- [ ] Normalize enrichment into `ReportItem.summary_zh`, `ReportItem.why_it_matters`, and `ReportItem.action_suggestion`.
- [ ] Preserve fallback behavior when enrichment omits an item.
- [ ] Run `pytest tests/test_summarizer.py -v` and confirm it passes.

### Task 6: Final Verification

**Files:**
- All touched files.

- [ ] Run `pytest -v` and confirm all tests pass.
- [ ] Run `OPENROUTER_API_KEY=dummy OPENROUTER_MODEL='~anthropic/claude-sonnet-latest' .venv/bin/github-daily-report dry-run --config config/sources.yml --output-dir reports --use-fixtures`.
- [ ] Inspect generated Markdown for Trending, Chinese item text, and expanded sections.
- [ ] Remove the fixture report generated by dry-run before committing.
- [ ] Commit and push the implementation.

## Self-Review

- Spec coverage: The plan covers real GitHub Trending, history-based deduplication, Chinese item explanation fields, expanded Skills/Agents discovery, expanded developer-news feeds, rendering, config, and tests.
- Deferred-work scan: No red-flag markers or vague deferred implementation steps remain.
- Type consistency: The plan consistently uses `ReportItem`, `summary_zh`, `why_it_matters`, `action_suggestion`, `GitHubTrendingSource`, `load_seen_urls`, and `seen_urls`.
