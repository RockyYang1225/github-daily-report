import json

import httpx
import respx

from github_daily_report.models import ReportItem
from github_daily_report.summarizer import FallbackSummarizer, FixtureSummarizer, OpenRouterSummarizer


@respx.mock
def test_openrouter_summarizer_returns_chinese_structured_content(sample_items):
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"executive_summary":"今日重点","recommendations":["试用工具"],"sections":{"今日必看":[]}}'
                        }
                    }
                ]
            },
        )
    )

    summarizer = OpenRouterSummarizer(api_key="key", model="test-model")
    content = summarizer.summarize(sample_items)

    assert route.called
    request = route.calls.last.request
    assert request is not None
    assert json.loads(request.content)["response_format"] == {"type": "json_object"}
    assert content.executive_summary == "今日重点"
    assert content.recommendations == ["试用工具"]


@respx.mock
def test_openrouter_summarizer_accepts_json_code_block(sample_items):
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '```json\n{"executive_summary":"今日重点","recommendations":["阅读论文"],"sections":{}}\n```'
                        }
                    }
                ]
            },
        )
    )

    summarizer = OpenRouterSummarizer(api_key="key", model="test-model")
    content = summarizer.summarize(sample_items)

    assert content.executive_summary == "今日重点"
    assert content.recommendations == ["阅读论文"]


@respx.mock
def test_openrouter_summarizer_normalizes_object_recommendations(sample_items):
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"executive_summary":"今日重点","recommendations":['
                                '{"priority":"高","action":"试用 agent-kit","reason":"适合构建 Agent 基础设施。"},'
                                '{"action":"阅读论文","reason":"了解长任务连续性。"}'
                                '],"sections":{}}'
                            )
                        }
                    }
                ]
            },
        )
    )

    summarizer = OpenRouterSummarizer(api_key="key", model="test-model")
    content = summarizer.summarize(sample_items)

    assert content.recommendations == [
        "高：试用 agent-kit。适合构建 Agent 基础设施。",
        "阅读论文。了解长任务连续性。",
    ]


@respx.mock
def test_openrouter_summarizer_enriches_items_by_url(sample_items):
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"executive_summary":"今日重点","recommendations":["试用工具"],'
                                '"item_enrichments":{'
                                '"https://github.com/acme/agent-kit":{'
                                '"summary_zh":"一个 Agent 工具包。",'
                                '"why_it_matters":"适合验证工具调用链路。",'
                                '"action_suggestion":"看 README 并跑 demo。",'
                                '"detail_zh":"这个项目适合用来搭建 Agent 原型。"'
                                "}}}"
                            )
                        }
                    }
                ]
            },
        )
    )

    summarizer = OpenRouterSummarizer(api_key="key", model="test-model")
    content = summarizer.summarize(sample_items)

    enriched = content.sections["GitHub 热门项目"][0]
    assert enriched.summary_zh == "一个 Agent 工具包。"
    assert enriched.why_it_matters == "适合验证工具调用链路。"
    assert enriched.action_suggestion == "看 README 并跑 demo。"
    assert enriched.detail_zh == "这个项目适合用来搭建 Agent 原型。"


def test_today_highlights_are_ten_and_other_sections_are_five_items():
    categories = ["github", "models", "papers", "developer-news", "skills"]
    items = []
    for category in categories:
        items.extend(
            ReportItem(
                title=f"{category}-{index}",
                url=f"https://example.com/{category}/{index}",
                source="Fixture",
                category=category,
                summary="A useful item",
                score_signals={"stars": 100 - index},
            )
            for index in range(12)
        )

    content = FixtureSummarizer().summarize(items)

    assert len(content.sections["今日必看"]) == 10
    assert len(content.sections["GitHub 热门项目"]) == 5
    assert len(content.sections["模型与数据集"]) == 5
    assert len(content.sections["论文与代码"]) == 5
    assert len(content.sections["AI 开发者资讯"]) == 5
    assert len(content.sections["Skills / Agents / 工具动态"]) == 5


def test_fallback_summarizer_builds_report_without_llm(sample_items):
    content = FallbackSummarizer().summarize(sample_items)

    assert "基础版" in content.executive_summary
    assert content.sections["今日必看"]
    assert content.sections["GitHub 热门项目"]
    assert content.recommendations
