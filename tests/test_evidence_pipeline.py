from app.harness.evidence_pipeline import EvidenceCollector, EvidenceValidator, HypothesisRouter


def test_evidence_collector_normalizes_search_and_sec_items():
    collector = EvidenceCollector()

    search_payload = {
        "data": [
            {
                "title": "Company wins AI contract",
                "url": "https://example.com/contract",
                "snippet": "Large federal AI contract awarded.",
                "source_name": "example.com",
            }
        ]
    }
    sec_items = [
        {
            "form": "8-K",
            "description": "Strategic partnership announcement",
            "url": "https://sec.gov/example",
            "filing_date": "2026-06-01",
        }
    ]

    search_items = collector._search_items(search_payload, ["ai", "contract"], "contract_search")
    filing_items = collector._sec_filing_items(sec_items)

    assert search_items[0]["topic_tags"] == ["ai", "contract"]
    assert search_items[0]["title"] == "Company wins AI contract"
    assert filing_items[0]["source_name"] == "sec.gov"
    assert "Strategic partnership" in filing_items[0]["title"]


def test_evidence_validator_dedupes_and_buckets():
    validator = EvidenceValidator()
    collected = {
        "raw_sources": {
            "sec_filings": {"data": [{"form": "8-K"}]},
            "market": {"data": {"news": []}},
            "jobs": {"data": []},
            "social": {"data": []},
            "gov_contracts": {"data": []},
            "patents": {"data": []},
        },
        "evidence_items": [
            {
                "source_type": "contract_search",
                "source_name": "sec.gov",
                "url": "https://sec.gov/x",
                "published_at": "2026-06-01",
                "title": "8-K strategic review",
                "raw_excerpt": "strategic review underway",
                "snippet": "strategic review underway",
                "entity_tags": [],
                "topic_tags": ["ma", "contract"],
            },
            {
                "source_type": "contract_search",
                "source_name": "sec.gov",
                "url": "https://sec.gov/x",
                "published_at": "2026-06-01",
                "title": "8-K strategic review",
                "raw_excerpt": "strategic review underway",
                "snippet": "strategic review underway",
                "entity_tags": [],
                "topic_tags": ["ma", "contract"],
            },
            {
                "source_type": "social",
                "source_name": "reddit.com",
                "url": "https://reddit.com/r/test",
                "published_at": "",
                "title": "Retail hype thread",
                "raw_excerpt": "hype hype",
                "snippet": "hype hype",
                "entity_tags": [],
                "topic_tags": ["noise"],
            },
        ],
    }

    validated = validator.validate(collected)

    assert validated["deduped_count"] == 2
    assert validated["by_hypothesis"]["ma"]["count"] == 1
    assert validated["by_hypothesis"]["contract"]["count"] == 1
    assert validated["by_hypothesis"]["noise"]["evidence"][0]["reliability"] == "D"
    assert "missing_jobs" in validated["missing_dimensions"]


def test_hypothesis_router_selects_sec_noise_and_top_topics():
    router = HypothesisRouter()
    validated = {
        "by_hypothesis": {
            "ai": {"count": 0, "total_reliability_score": 0},
            "contract": {"count": 2, "total_reliability_score": 6},
            "earnings": {"count": 1, "total_reliability_score": 2},
            "ma": {"count": 0, "total_reliability_score": 0},
            "regulatory": {"count": 0, "total_reliability_score": 0},
            "noise": {"count": 3, "total_reliability_score": 4},
        }
    }
    route = router.route(validated, {"normalized_contract": {"dte": 9, "underlying_move_5d": 0.12}})

    assert route["selected_agents"][0] == "sec_filings_agent"
    assert "public_attention_noise_agent" in route["selected_agents"]
    assert "major_contract_agent" in route["selected_agents"]
    assert "earnings_surprise_agent" in route["selected_agents"]
