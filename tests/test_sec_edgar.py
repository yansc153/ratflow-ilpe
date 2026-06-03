import pytest

from app.data_sources.sec_edgar import SECEdgarAdapter


class DummyResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class DummyClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        self.calls.append(url)
        for key, payload in self.responses.items():
            if key in url:
                return DummyResponse(payload)
        raise AssertionError(f"Unexpected URL: {url}")


@pytest.mark.asyncio
async def test_sec_edgar_adapter_parses_recent_filings(monkeypatch):
    company_payload = {
        "0": {"ticker": "NOC", "cik_str": 1133421},
    }
    submissions_payload = {
        "filings": {
            "recent": {
                "form": ["8-K", "10-Q"],
                "accessionNumber": ["0001133421-24-000001", "0001133421-24-000002"],
                "filingDate": ["2026-05-01", "2026-04-25"],
                "primaryDocument": ["a8k.htm", "q1.htm"],
                "primaryDocDescription": ["Current report", "Quarterly report"],
            }
        }
    }

    dummy = DummyClient({
        "company_tickers.json": company_payload,
        "CIK0001133421.json": submissions_payload,
    })

    monkeypatch.setattr(
        "app.data_sources.sec_edgar.httpx.AsyncClient",
        lambda **kwargs: dummy,
    )

    adapter = SECEdgarAdapter()
    filings = await adapter.get_recent_filings("NOC", limit=2)

    assert len(filings) == 2
    assert filings[0]["form"] == "8-K"
    assert filings[0]["url"].endswith("/000113342124000001/a8k.htm")
    assert filings[1]["form"] == "10-Q"
