from github_daily_report.sources.skills import SkillsDirectorySource, parse_skills_directory


SKILLS_SH_FIXTURE = r"""
<script>
self.__next_f.push([1,"{\"source\":\"vercel-labs/skills\",\"skillId\":\"find-skills\",\"name\":\"find-skills\",\"installs\":2270087,\"weeklyInstalls\":[10,20,30],\"isOfficial\":true},{\"source\":\"anthropics/skills\",\"skillId\":\"frontend-design\",\"name\":\"frontend-design\",\"installs\":607811,\"weeklyInstalls\":[1,2,3]}"])
</script>
"""


def test_parse_skills_directory_extracts_embedded_skill_rankings():
    items = parse_skills_directory(SKILLS_SH_FIXTURE, limit=2)

    assert len(items) == 2
    assert items[0].title == "vercel-labs/skills/find-skills"
    assert items[0].url == "https://www.skills.sh/vercel-labs/skills/find-skills"
    assert items[0].source == "skills.sh"
    assert items[0].category == "skills"
    assert "2,270,087 installs" in items[0].summary
    assert "official" in items[0].tags
    assert items[0].score_signals["installs"] == 2270087
    assert items[0].score_signals["weekly_installs"] == 60


def test_skills_directory_source_fetches_homepage(monkeypatch):
    class Response:
        text = SKILLS_SH_FIXTURE

        def raise_for_status(self):
            return None

    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr("github_daily_report.sources.skills.httpx.get", fake_get)

    result = SkillsDirectorySource(limit=1).fetch()

    assert calls[0][0] == "https://www.skills.sh/"
    assert result.source == "skills.sh"
    assert result.items[0].title == "vercel-labs/skills/find-skills"
    assert result.warnings == []
