# Content Quality Upgrade Design

Date: 2026-05-17
Status: Approved for implementation planning

## Goal

Improve the daily AI developer report so it feels fresh, more useful, and more readable in Chinese.

This upgrade addresses five product issues:

- add real GitHub Trending coverage;
- add Chinese explanations for each recommended item;
- reduce repeated GitHub hot project recommendations across days;
- expand Skills / Agents / tooling coverage;
- expand AI developer news coverage.

## Non-Goals

- Do not add a database.
- Do not add a web dashboard.
- Do not personalize by user clicks or reading history.
- Do not build a complex crawler framework.
- Do not remove the existing GitHub Search, RSS, OpenRouter, Markdown, HTML, SMTP, or GitHub Actions flow.

## Recommended Approach

Keep the existing Python CLI pipeline and add content-quality modules around it.

The upgraded flow is:

```text
collect sources
  -> collect recently seen report URLs from reports/*.md
  -> normalize items
  -> filter recently seen URLs
  -> rank with diversity
  -> ask OpenRouter for Chinese enrichment
  -> render richer Markdown and HTML
  -> archive and email
```

The project should stay simple enough to run entirely inside GitHub Actions.

## Source Changes

### GitHub Trending

Add a real `GitHubTrendingSource` in `src/github_daily_report/sources/github.py`.

It fetches GitHub Trending pages such as:

- `https://github.com/trending?since=daily`
- `https://github.com/trending?since=weekly`
- optional language-specific pages when configured.

The parser extracts:

- repository full name;
- repository URL;
- description;
- language when present;
- total stars when present;
- stars gained during the selected period when present;
- trending period, such as `daily` or `weekly`.

Trending items use:

```text
category = "github"
source = "GitHub Trending Daily" or "GitHub Trending Weekly"
```

The existing `GitHubSearchSource` remains. Trending answers “what is hot now”; Search answers “what AI projects match our explicit interests.”

### Skills / Agents / Tooling

Expand Skills / Agents / tooling discovery through configured GitHub queries and RSS feeds.

Initial query themes:

- agent skills;
- MCP servers and clients;
- Claude Code;
- Codex;
- Cursor;
- OpenAI Agents SDK;
- browser-use and browser automation;
- workflow automation for developers;
- prompt engineering tools;
- RAG and eval tooling.

The first implementation may keep this as GitHub Search plus RSS. It should not introduce site-specific scrapers for every tool source.

### AI Developer News

Expand RSS sources with more developer-focused sources.

Candidate additions:

- OpenRouter announcements or blog if available;
- Model Context Protocol / Anthropic engineering sources;
- Cursor changelog or blog;
- Simon Willison;
- Latent Space;
- The Batch;
- Papers with Code;
- Google Research or Google AI developer blog;
- Microsoft AI developer blog;
- GitHub Changelog;
- Vercel AI SDK related posts.

Each feed should have a per-source limit so news does not dominate the report.

## History-Based Deduplication

Add `src/github_daily_report/history.py`.

It reads recent Markdown reports from:

```text
reports/*.md
```

The first version uses a 14-day window.

Responsibilities:

- parse Markdown links with a simple, tested regex;
- normalize URLs by lowercasing scheme and host and removing trailing slashes;
- return a set of recently seen URLs;
- expose enough status information to report how many candidate items were skipped.

Ranking should prefer unseen items. For the first version, seen items are filtered out before final ranking. If filtering removes too much content, the system may allow seen items back as a last-resort fallback, but unseen items must always be preferred.

This solves the specific issue that `GitHub 热门项目` currently looks similar from day to day.

## Chinese Item Enrichment

Extend the model layer so each selected `ReportItem` can carry Chinese editorial text.

Add optional fields:

```text
summary_zh
why_it_matters
```

OpenRouter should enrich selected items after ranking. The enrichment prompt should ask for a strict JSON object keyed by item URL or stable item id. For each item it should return:

- short Chinese explanation;
- why it matters to AI developers;
- optional action suggestion.

The renderer should display, per item:

- original title;
- source;
- Chinese explanation;
- why it matters;
- original link.

Fallback behavior:

- If OpenRouter omits an item, use the original item summary as a fallback.
- If a field is missing, render only the fields that exist.
- The report must not fail solely because one item lacks enrichment.

The existing executive summary and recommendations remain.

## Ranking and Report Composition

Keep final report size controlled, but allow more candidate depth.

Recommended limits:

- collect more raw GitHub, Skills, and RSS candidates than before;
- apply history filtering;
- preserve category diversity;
- final report still targets roughly 15-30 core items.

`GitHub 热门项目` should combine:

- GitHub Trending daily;
- GitHub Trending weekly;
- GitHub AI Search.

Scoring signals should include:

- stars gained during trending period;
- total stars;
- recency;
- AI keyword relevance;
- source type;
- whether the URL was recently seen.

## Configuration

Extend `config/sources.yml` with:

```text
history:
  lookback_days: 14

github_trending:
  enabled: true
  periods: [daily, weekly]
  languages: []

skills_queries:
  - agent skills MCP
  - Claude Code agent
  - OpenAI Agents SDK

news_feeds:
  ...
```

The exact YAML shape can follow the existing config style, but it must remain human-editable.

## Rendering

Markdown and HTML rendering should keep the current section order:

1. 今日必看
2. GitHub 热门项目
3. 模型与数据集
4. 论文与代码
5. AI 开发者资讯
6. Skills / Agents / 工具动态
7. 今日行动建议
8. 抓取状态与失败来源

Each item should render richer Chinese text when available.

Example item shape:

```text
- acme/agent-kit
  来源：GitHub Trending Daily
  说明：一个用于构建 Agent 工作流的工具包。
  值得关注：它把工具调用、状态管理和执行链路放在一起，适合做 Agent 原型。
  链接：https://github.com/acme/agent-kit
```

## Error Handling

- GitHub Trending fetch failure: record warning, continue with GitHub Search.
- History parsing failure for one report file: record warning and continue with other files.
- OpenRouter item enrichment partial failure: keep original summaries and continue.
- OpenRouter total failure: keep the existing critical-failure behavior for report summary generation.
- Too many seen items filtered: allow fallback items only after unseen items are exhausted.

## Testing Strategy

Add tests for:

- parsing GitHub Trending HTML fixture;
- extracting recently seen URLs from Markdown reports;
- filtering seen URLs before ranking;
- preserving fallback content when enrichment misses an item;
- rendering `summary_zh` and `why_it_matters`;
- expanded Skills and news config loading.

## Acceptance Criteria

- The report includes real GitHub Trending candidates.
- `GitHub 热门项目` avoids recommending URLs found in recent archived reports when enough unseen alternatives exist.
- Each displayed item can show Chinese explanation and why-it-matters text.
- Skills / Agents / tooling candidates are broader than a single static entry.
- AI developer news candidates come from a larger developer-focused feed list.
- Existing tests still pass, and new tests cover the new parsing, history, enrichment, and rendering behavior.
