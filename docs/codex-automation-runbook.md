# Codex Gmail Report Runbook

This runbook is the source of truth for the scheduled Codex report task. Follow the steps in order and stop on any failed precondition.

## Fixed Settings

- Timezone: `Asia/Shanghai`
- Sender: authenticated Gmail account `rockyyang951225@gmail.com`
- Recipients: `rockyyang951225@gmail.com`, `zoeyli1997@gmail.com`
- Subject: `AI 开发者日报 - YYYY-MM-DD`
- Candidate JSON: `/tmp/github-daily-report-candidates.json`
- Codex draft JSON: `/tmp/github-daily-report-draft.json`
- Email HTML: `/tmp/github-daily-report.html`

The user has explicitly authorized unattended delivery of this report to both recipients.

## Procedure

1. Compute today's `YYYY-MM-DD` in `Asia/Shanghai`. Use this date in the subject and report filename.
2. Use `$gmail:gmail` to search sent mail for the exact subject `AI 开发者日报 - YYYY-MM-DD`.
3. Inspect matching messages. If a message was already sent to both configured recipients, stop without collecting or sending and report that the run was skipped.
4. If the Gmail duplicate check fails, stop. Do not risk a duplicate send.
5. Run `git pull --ff-only origin main`. Stop on failure and do not modify unrelated files.
6. Run:

   ```bash
   .venv/bin/python -m github_daily_report collect \
     --config config/sources.yml \
     --reports-dir reports \
     --output /tmp/github-daily-report-candidates.json
   ```

7. Read the candidate JSON. If `items` is empty, stop without sending.
8. Create `/tmp/github-daily-report-draft.json` with this shape:

   ```json
   {
     "executive_summary": "A concise Chinese overview of today's most useful signals.",
     "recommendations": ["At least one concrete action in Chinese."],
     "item_enrichments": {
       "https://original-item-url.example": {
         "summary_zh": "A factual Chinese introduction.",
         "why_it_matters": "Why this item matters to AI developers.",
         "action_suggestion": "One concrete next action.",
         "detail_zh": "Who it suits, what it does, and a realistic trial scenario."
       }
     }
   }
   ```

9. `item_enrichments` must contain every candidate URL as a key. Every field must be non-empty Chinese text. Preserve facts and links from the candidate data; never invent capabilities. When evidence is thin, state only what the source description supports.
10. Run:

    ```bash
    .venv/bin/python -m github_daily_report render-codex \
      --candidates /tmp/github-daily-report-candidates.json \
      --draft /tmp/github-daily-report-draft.json \
      --output-dir reports \
      --html-output /tmp/github-daily-report.html
    ```

11. Confirm `reports/YYYY-MM-DD.md` and `/tmp/github-daily-report.html` exist and are non-empty. Confirm the subject date matches the report date.
12. Send the HTML through Gmail from the authenticated account to `rockyyang951225@gmail.com, zoeyli1997@gmail.com` with the exact subject. Send directly; do not create a draft.
13. After Gmail confirms success, stage only `reports/YYYY-MM-DD.md`, commit with `chore: archive daily report`, and push `main`.
14. Report the Gmail message id and Git commit id.

## Failure Rules

- Collection failure: do not send an empty or partial report.
- Codex generation or validation failure: do not send an incomplete report.
- Gmail failure: keep the local report for diagnosis; do not claim delivery.
- Git failure after successful Gmail delivery: report `邮件已发送、归档失败`. Do not resend. The next run must rely on the sent-mail duplicate check.
- Never stage `.DS_Store`, `docs/knowledge/`, `docs/resume-project-guide.md`, or unrelated local changes.
- Never use OpenRouter or SMTP in this scheduled workflow.
