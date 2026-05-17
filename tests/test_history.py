from datetime import date

from github_daily_report.history import extract_markdown_links, load_seen_urls, normalize_url


def test_normalize_url_removes_trailing_slash_and_lowercases_host():
    assert normalize_url("HTTPS://GitHub.com/Acme/Tool/") == "https://github.com/Acme/Tool"


def test_extract_markdown_links_from_report_text():
    text = "- [agent-kit](https://github.com/acme/agent-kit)\n- plain https://example.com/nope\n"

    assert extract_markdown_links(text) == {"https://github.com/acme/agent-kit"}


def test_load_seen_urls_reads_recent_report_files(tmp_path):
    recent = tmp_path / "2026-05-17.md"
    old = tmp_path / "2026-04-01.md"
    recent.write_text("[new](https://github.com/acme/new)", encoding="utf-8")
    old.write_text("[old](https://github.com/acme/old)", encoding="utf-8")

    seen = load_seen_urls(tmp_path, today=date(2026, 5, 17), lookback_days=14)

    assert "https://github.com/acme/new" in seen.urls
    assert "https://github.com/acme/old" not in seen.urls
    assert seen.files_read == 1
