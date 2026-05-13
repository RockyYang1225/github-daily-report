# GitHub Daily Report Design

Date: 2026-05-13
Status: Approved for implementation planning

## Goal

Build a GitHub Actions powered daily report system that collects high-signal developer AI information, summarizes it in Chinese with OpenRouter, sends the report by SMTP email, and archives a Markdown copy in the repository.

The report should prioritize practical value for developers and personal learning: useful open source projects, AI tools, model and dataset updates, papers with code, agent skills, framework updates, tutorials, and actionable recommendations. It should avoid becoming a broad industry news digest.

## Non-Goals

- No web dashboard in the first version.
- No database in the first version.
- No paid email provider integration in the first version.
- No fully automated model selection. The OpenRouter model is configured explicitly.
- No attempt to exhaustively capture every AI news item. The report should be selective.

## Recommended Approach

Use a Python CLI application scheduled by GitHub Actions.

GitHub Actions runs daily on a Beijing time schedule, installs the Python project, executes the report command, commits the Markdown report to `reports/YYYY-MM-DD.md`, uploads it as a workflow artifact, and sends an HTML version by SMTP.

Python is the preferred first implementation because it is a good fit for RSS parsing, API clients, data normalization, email rendering, and command-line automation.

## High-Level Flow

```text
GitHub Actions
  -> Python CLI
  -> collect source items
  -> normalize, deduplicate, rank, and limit items
  -> summarize with OpenRouter
  -> render Markdown and HTML
  -> save Markdown report
  -> send HTML email with SMTP
```

## Architecture

### CLI Layer

The project exposes a CLI entry point with at least two modes:

- `run`: generates the report, writes Markdown, sends email, and returns a non-zero exit code on critical failure.
- `dry-run`: generates the report without sending email. This is used for local debugging and workflow validation.

The CLI validates required configuration before doing network work. Missing secrets should produce a clear error naming the missing configuration key.

### Source Layer

Each source is implemented as an independent module with a shared interface. A source fetches raw data, parses it, and returns a `SourceResult`.

Initial sources:

- GitHub Trending: popular repositories by language or global trend.
- GitHub AI Search: repositories matching AI keywords, ranked by stars, recent activity, and relevance.
- Hugging Face: trending or recently updated models, datasets, and Spaces.
- Papers with Code: recent or trending AI papers with available implementation links where possible.
- arXiv: recent AI papers from categories such as `cs.AI`, `cs.LG`, `cs.CL`, and `cs.CV`.
- RSS: developer-focused AI feeds such as OpenAI, Anthropic, Google DeepMind, Hugging Face Blog, LangChain, LlamaIndex, Vercel AI, GitHub Blog, and similar sources.
- Skills and agent tools: agent skills, MCP, Codex, Claude Code, Gemini CLI, prompt engineering, developer automation tools, and practical tutorials discovered through RSS, GitHub search, and configured fixed sources.

Source failures are isolated. A failed source is recorded as a warning and should not stop the whole report unless every useful source fails.

### Data Model

Use a small set of shared data structures:

- `ReportItem`: a normalized item with title, URL, source name, category, summary or description, published or updated time, tags, score signals, and optional metadata.
- `SourceResult`: source name, successful items, warning messages, and error information if the source partially or fully failed.
- `DailyReport`: report date, selected sections, generated Markdown, generated HTML, and collection status.

All downstream stages consume normalized `ReportItem` objects so that new sources can be added without changing the summarizer or renderer contracts.

### Normalize, Rank, and Limit Layer

The ranking layer turns raw source outputs into a compact, high-signal candidate set.

Responsibilities:

- Deduplicate by URL, canonical repository URL, paper identifier, and normalized title.
- Filter out low-value or irrelevant items using configured keywords and category rules.
- Score items using available signals such as stars, recent star growth, likes, downloads, recency, source reliability, and keyword relevance.
- Preserve diversity across categories so one source does not dominate the report.
- Limit the final report to roughly 10-25 core items.

The ranking behavior should be deterministic enough to test with fixture data.

### Summarizer Layer

Use OpenRouter as the default LLM provider through an OpenAI-compatible API client.

Required secret configuration:

- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`

Optional configuration:

- `OPENROUTER_BASE_URL`, defaulting to `https://openrouter.ai/api/v1`

The model is not hard-coded. Documentation can recommend candidates, but the workflow requires `OPENROUTER_MODEL` to be set. This keeps the project flexible across cost, speed, and quality preferences.

The summarizer produces a Chinese report with:

- a concise executive summary;
- the most important items and why they matter;
- category-specific summaries;
- links to original sources;
- practical recommendations for what to try, read, or save.

If OpenRouter fails, the run should fail rather than sending a low-quality or empty report.

### Renderer Layer

Render both Markdown and HTML from the same structured report content.

Markdown is saved to:

```text
reports/YYYY-MM-DD.md
```

HTML is used as the email body. The HTML should be simple, email-client friendly, and readable without external assets.

### Mailer Layer

Use SMTP for the first version.

Required secret configuration:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `MAIL_FROM`
- `MAIL_TO`

The mailer supports dry-run mode so tests and local validation do not send real email.

If SMTP sending fails after a report is generated, the report should still be kept as a file and uploaded as an artifact. The workflow should fail visibly so the delivery problem can be fixed.

## Public Configuration

Public, non-secret configuration lives in `config/sources.yml`.

This file controls:

- report title;
- timezone, defaulting to `Asia/Shanghai`;
- language, defaulting to Chinese;
- maximum items per source;
- final report item limit;
- keywords for AI relevance;
- RSS feed list;
- source enablement flags;
- source-specific query settings.

Example keyword themes:

```text
AI, LLM, Agent, MCP, RAG, OpenAI, Claude, Gemini, Cursor, Codex,
LangChain, LlamaIndex, Hugging Face, diffusion, embedding
```

## GitHub Actions Workflow

The workflow runs daily on a schedule aligned with Beijing morning time. It should also support manual dispatch for debugging.

Workflow responsibilities:

- check out the repository;
- set up Python;
- install dependencies;
- run tests when available;
- run the daily report CLI;
- upload the Markdown report as an artifact;
- commit the Markdown report back to the repository;
- send the HTML email.

The workflow uses GitHub Secrets for OpenRouter and SMTP credentials.

## Report Structure

The email and Markdown report should use these sections:

1. 今日必看
2. GitHub 热门项目
3. 模型与数据集
4. 论文与代码
5. AI 开发者资讯
6. Skills / Agents / 工具动态
7. 今日行动建议
8. 抓取状态与失败来源

The report should be selective. The expected first-version range is 10-25 core items, with short explanations and original links.

## Failure Handling

- Single source failure: continue the report and list the failed source in the status section.
- Multiple source failures with enough remaining content: continue and include warnings.
- Too little content: send a low-content report that explains the issue and includes source status.
- OpenRouter failure: fail the workflow and do not send an empty report.
- SMTP failure: keep the generated report, upload it as an artifact, and fail the workflow.
- Missing secret: fail fast with a clear configuration error.
- Parsing failure for one item: skip that item, record a warning, and continue the source.

## Testing Strategy

Initial tests should cover:

- source parsers using fixture responses;
- normalization and deduplication;
- ranking and category diversity;
- renderer output for Markdown and HTML structure;
- mailer dry-run behavior;
- CLI configuration validation;
- CLI dry-run behavior.

Network-heavy behavior should be isolated behind source interfaces so tests can use fixtures and mocks.

## First Implementation Scope

The first implementation should include:

- Python project scaffold;
- CLI with `run` and `dry-run`;
- shared models;
- public YAML config;
- source modules for GitHub, Hugging Face, Papers with Code, arXiv, RSS, and Skills/Agents discovery;
- ranking and limiting;
- OpenRouter summarizer;
- Markdown and HTML rendering;
- SMTP mailer;
- GitHub Actions workflow;
- basic tests and fixture structure;
- README setup instructions for GitHub Secrets.

The implementation may keep individual source strategies simple at first as long as module boundaries are clear and failures are isolated.

## Open Questions Resolved

- Runtime location: GitHub Actions.
- Email delivery: SMTP.
- Content scope: full scope, including GitHub, Hugging Face, Papers with Code, arXiv, RSS, and Skills/Agents/tools.
- Report style: developer practical plus personal learning.
- Summary provider: OpenRouter.
- Model choice: configured through `OPENROUTER_MODEL`, not decided in code.
- Output language and format: Chinese HTML email plus Markdown archive in the repository.
