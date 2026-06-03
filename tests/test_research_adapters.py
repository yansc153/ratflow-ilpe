import pytest

from app.agents.ai_transformation_agent import AITransformationAgent
from app.data_sources.news_search import NewsSearchAdapter
from app.data_sources.website_research import WebsiteResearchAdapter


def test_news_search_parses_duckduckgo_results():
    html = """
    <html><body>
      <div class="result">
        <a class="result__a" href="https://example.com/ai-news">Example AI News</a>
        <a class="result__snippet">Example snippet about AI partnerships.</a>
      </div>
    </body></html>
    """

    results = NewsSearchAdapter._parse_duckduckgo_results(html, max_results=5)

    assert len(results) == 1
    assert results[0]["title"] == "Example AI News"
    assert results[0]["url"] == "https://example.com/ai-news"
    assert "AI partnerships" in results[0]["snippet"]


def test_website_research_extracts_summary():
    html = """
    <html>
      <head>
        <title>Investor Relations</title>
        <meta name="description" content="Company IR page">
      </head>
      <body>
        <p>First paragraph.</p>
        <p>Second paragraph.</p>
      </body>
    </html>
    """

    data = WebsiteResearchAdapter._extract_page_summary(html, "https://example.com/ir")

    assert data["title"] == "Investor Relations"
    assert data["description"] == "Company IR page"
    assert "First paragraph." in data["text_excerpt"]


@pytest.mark.asyncio
async def test_ai_agent_attaches_retrieved_context(monkeypatch):
    async def fake_fetch(*args, **kwargs):
        return {"data": [{"title": "AI launch", "url": "https://example.com"}]}

    async def fake_chat(**kwargs):
        return {
            "score": 55,
            "confidence": "medium",
            "summary": "Observed AI launch clues",
            "positive_evidence": [],
            "negative_evidence": [],
            "uncertainties": [],
            "errors": [],
        }

    agent = AITransformationAgent()
    monkeypatch.setattr(agent.search, "fetch", fake_fetch)
    monkeypatch.setattr(agent.jobs, "fetch", fake_fetch)
    monkeypatch.setattr("app.agents.ai_transformation_agent.deepseek.chat", fake_chat)

    output = await agent.run({"case_uid": "CASE1", "alert": {"ticker": "NOC", "company_name": "Northrop"}})

    assert output["score"] == 55
    assert output["retrieved_context"]["web"][0]["title"] == "AI launch"
    assert output["retrieved_context"]["jobs"][0]["title"] == "AI launch"
