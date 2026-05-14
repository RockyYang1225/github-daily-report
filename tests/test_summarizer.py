import httpx
import respx

from github_daily_report.summarizer import OpenRouterSummarizer


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
    assert content.executive_summary == "今日重点"
    assert content.recommendations == ["试用工具"]
