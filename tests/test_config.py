import pytest

from github_daily_report.config import ConfigError, load_env_config, load_public_config


def test_load_public_config_reads_limits_and_feeds(tmp_path):
    path = tmp_path / "sources.yml"
    path.write_text(
        """
report:
  title: AI Developer Daily
  timezone: Asia/Shanghai
  language: zh-CN
limits:
  per_source: 5
  final_items: 15
keywords: [AI, LLM, Agent]
rss_feeds:
  - name: OpenAI
    url: https://openai.com/news/rss.xml
sources:
  github: true
""",
        encoding="utf-8",
    )

    config = load_public_config(path)

    assert config.report.title == "AI Developer Daily"
    assert config.limits.final_items == 15
    assert config.rss_feeds[0].name == "OpenAI"


def test_load_env_config_names_missing_required_keys(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("MAIL_FROM", raising=False)
    monkeypatch.delenv("MAIL_TO", raising=False)

    with pytest.raises(ConfigError) as exc:
        load_env_config(send_email=True)

    message = str(exc.value)
    assert "OPENROUTER_API_KEY" in message
    assert "OPENROUTER_MODEL" in message
    assert "SMTP_HOST" in message
