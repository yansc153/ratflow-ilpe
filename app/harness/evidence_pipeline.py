from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Dict, Iterable, List

from app.data_sources.market_context import YFinanceResearchAdapter
from app.data_sources.news_search import NewsSearchAdapter
from app.data_sources.sec_edgar import SECEdgarAdapter
from app.data_sources.website_research import (
    GovContractsResearchAdapter,
    JobsResearchAdapter,
    PatentsResearchAdapter,
    PriceDataAdapter,
    SocialResearchAdapter,
)


TOPIC_AI = "ai"
TOPIC_CONTRACT = "contract"
TOPIC_EARNINGS = "earnings"
TOPIC_MA = "ma"
TOPIC_REGULATORY = "regulatory"
TOPIC_NOISE = "noise"

HYPOTHESIS_TOPICS = [
    TOPIC_AI,
    TOPIC_CONTRACT,
    TOPIC_EARNINGS,
    TOPIC_MA,
    TOPIC_REGULATORY,
    TOPIC_NOISE,
]


class EvidenceCollector:
    def __init__(self):
        self.search = NewsSearchAdapter()
        self.jobs = JobsResearchAdapter()
        self.social = SocialResearchAdapter()
        self.gov = GovContractsResearchAdapter()
        self.patents = PatentsResearchAdapter()
        self.market = YFinanceResearchAdapter()
        self.price = PriceDataAdapter()
        self.sec = SECEdgarAdapter()

    async def collect(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        alert = case_data.get("alert", {})
        ticker = alert.get("ticker", "")
        company = alert.get("company_name", ticker)

        tasks = {
            "ai_search": self.search.fetch(
                query=f'"{company}" AI product partnership investor relations careers',
                max_results=8,
            ),
            "contract_search": self.search.fetch(
                query=f'"{company}" contract award customer partnership backlog bookings',
                max_results=6,
            ),
            "earnings_search": self.search.fetch(
                query=f"{ticker} earnings guidance analyst estimate revisions",
                max_results=6,
            ),
            "ma_search": self.search.fetch(
                query=f'"{company}" strategic review activist 13D tender offer asset sale restructuring',
                max_results=6,
            ),
            "regulatory_search": self.search.fetch(
                query=f'"{company}" patent litigation regulatory approval FDA lawsuit',
                max_results=6,
            ),
            "noise_search": self.search.fetch(
                query=f"{ticker} stock news unusual options hype earnings",
                max_results=6,
            ),
            "jobs": self.jobs.fetch(company=company),
            "social": self.social.fetch(ticker=ticker),
            "gov_contracts": self.gov.fetch(company=company),
            "patents": self.patents.fetch(company=company),
            "market": self.market.fetch(ticker=ticker),
            "price": self.price.fetch(ticker=ticker),
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        raw_sources: Dict[str, Any] = {}
        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                raw_sources[key] = {"source": key, "status": "error", "error": str(result), "data": []}
            else:
                raw_sources[key] = result

        try:
            filings = await self.sec.get_recent_filings(ticker, limit=8)
        except Exception as exc:
            filings = []
            raw_sources["sec_filings"] = {"source": "sec_filings", "status": "error", "error": str(exc), "data": []}
        else:
            raw_sources["sec_filings"] = {"source": "sec_filings", "status": "ok", "data": filings}

        evidence_items: List[Dict[str, Any]] = []
        evidence_items.extend(self._search_items(raw_sources["ai_search"], [TOPIC_AI], "ai_search"))
        evidence_items.extend(self._search_items(raw_sources["contract_search"], [TOPIC_CONTRACT], "contract_search"))
        evidence_items.extend(self._search_items(raw_sources["earnings_search"], [TOPIC_EARNINGS], "earnings_search"))
        evidence_items.extend(self._search_items(raw_sources["ma_search"], [TOPIC_MA], "ma_search"))
        evidence_items.extend(self._search_items(raw_sources["regulatory_search"], [TOPIC_REGULATORY], "regulatory_search"))
        evidence_items.extend(self._search_items(raw_sources["noise_search"], [TOPIC_NOISE], "noise_search"))
        evidence_items.extend(self._search_items(raw_sources["jobs"], [TOPIC_AI], "jobs"))
        evidence_items.extend(self._search_items(raw_sources["social"], [TOPIC_NOISE], "social"))
        evidence_items.extend(self._search_items(raw_sources["gov_contracts"], [TOPIC_CONTRACT], "gov_contracts"))
        evidence_items.extend(self._search_items(raw_sources["patents"], [TOPIC_REGULATORY], "patents"))
        evidence_items.extend(self._market_news_items(raw_sources["market"]))
        evidence_items.extend(self._sec_filing_items(filings))

        return {
            "raw_sources": raw_sources,
            "evidence_items": evidence_items,
            "collection_summary": {
                "ticker": ticker,
                "company": company,
                "raw_source_count": len(raw_sources),
                "evidence_item_count": len(evidence_items),
            },
        }

    @staticmethod
    def _search_items(source_payload: Dict[str, Any], topic_tags: List[str], source_key: str) -> List[Dict[str, Any]]:
        items = []
        for item in source_payload.get("data", []) or []:
            title = item.get("title", "")
            url = item.get("url", "")
            snippet = item.get("snippet", "") or item.get("summary", "")
            if not title and not snippet:
                continue
            items.append(
                {
                    "source_type": source_key,
                    "source_name": item.get("source_name") or source_key,
                    "url": url,
                    "published_at": item.get("published_at") or item.get("date", ""),
                    "title": title or source_key,
                    "raw_excerpt": snippet,
                    "snippet": snippet,
                    "entity_tags": [],
                    "topic_tags": list(topic_tags),
                }
            )
        return items

    @staticmethod
    def _market_news_items(source_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = []
        news_items = ((source_payload.get("data") or {}).get("news") or []) if isinstance(source_payload, dict) else []
        for item in news_items:
            summary = item.get("summary", "")
            title = item.get("title", "")
            if not title and not summary:
                continue
            items.append(
                {
                    "source_type": "market_news",
                    "source_name": item.get("provider", "") or "yfinance",
                    "url": item.get("url", ""),
                    "published_at": item.get("published_at", ""),
                    "title": title or "market_news",
                    "raw_excerpt": summary,
                    "snippet": summary,
                    "entity_tags": [],
                    "topic_tags": [TOPIC_EARNINGS, TOPIC_NOISE],
                }
            )
        return items

    @staticmethod
    def _sec_filing_items(filings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        items = []
        for filing in filings:
            title = f"{filing.get('form', '')} {filing.get('description', '')}".strip()
            items.append(
                {
                    "source_type": "sec_filing_index",
                    "source_name": "sec.gov",
                    "url": filing.get("url", ""),
                    "published_at": filing.get("filing_date", ""),
                    "title": title or filing.get("primary_document", "sec_filing"),
                    "raw_excerpt": filing.get("description", "") or filing.get("primary_document", ""),
                    "snippet": filing.get("description", "") or filing.get("primary_document", ""),
                    "entity_tags": [],
                    "topic_tags": [TOPIC_CONTRACT, TOPIC_MA, TOPIC_REGULATORY, TOPIC_EARNINGS],
                }
            )
        return items


class EvidenceValidator:
    RELIABILITY_SCORES = {"A": 4, "B": 3, "C": 2, "D": 1}

    def validate(self, collected: Dict[str, Any]) -> Dict[str, Any]:
        deduped = self._dedupe(collected.get("evidence_items", []))
        for item in deduped:
            item["reliability"] = self._infer_reliability(item)
            item["reliability_score"] = self.RELIABILITY_SCORES[item["reliability"]]

        by_topic: Dict[str, Dict[str, Any]] = {}
        for topic in HYPOTHESIS_TOPICS:
            topic_items = [item for item in deduped if topic in item.get("topic_tags", [])]
            topic_items = sorted(
                topic_items,
                key=lambda item: (item.get("reliability_score", 0), len(item.get("snippet", ""))),
                reverse=True,
            )
            by_topic[topic] = {
                "count": len(topic_items),
                "evidence": topic_items[:6],
                "sources": sorted({item.get("source_name", "") for item in topic_items if item.get("source_name")}),
                "total_reliability_score": sum(item.get("reliability_score", 0) for item in topic_items),
            }

        raw_sources = collected.get("raw_sources", {})
        missing_dimensions = []
        for key in ["sec_filings", "market", "jobs", "social", "gov_contracts", "patents"]:
            payload = raw_sources.get(key, {})
            data = payload.get("data", [])
            if not data:
                missing_dimensions.append(f"missing_{key}")

        conflicts = []
        if by_topic[TOPIC_NOISE]["count"] >= 3 and sum(by_topic[t]["count"] for t in [TOPIC_AI, TOPIC_CONTRACT, TOPIC_EARNINGS, TOPIC_MA, TOPIC_REGULATORY]) <= 2:
            conflicts.append("public_noise_dominates_signal")

        return {
            "all_evidence": deduped,
            "all_evidence_count": len(deduped),
            "deduped_count": len(deduped),
            "missing_dimensions": missing_dimensions,
            "conflicts": conflicts,
            "by_hypothesis": by_topic,
            "source_context": raw_sources,
            "summary": self._summary(by_topic, missing_dimensions, conflicts),
        }

    @staticmethod
    def _dedupe(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped = []
        seen = set()
        for item in items:
            key = (
                item.get("url", "").strip().lower(),
                item.get("title", "").strip().lower(),
                item.get("snippet", "").strip().lower()[:180],
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(dict(item))
        return deduped

    @staticmethod
    def _infer_reliability(item: Dict[str, Any]) -> str:
        source_name = (item.get("source_name") or "").lower()
        url = (item.get("url") or "").lower()
        host = source_name or url
        if "sec.gov" in host or ".gov" in host:
            return "A"
        if "yahoo" in host or "investor" in host or "ir." in host:
            return "B"
        if any(token in host for token in ["reddit", "stocktwits", "x.com", "twitter"]):
            return "D"
        if host:
            return "C"
        return "D"

    @staticmethod
    def _summary(by_topic: Dict[str, Dict[str, Any]], missing_dimensions: List[str], conflicts: List[str]) -> str:
        topic_parts = [f"{topic}:{bucket['count']}" for topic, bucket in by_topic.items() if bucket["count"]]
        summary = " | ".join(topic_parts) if topic_parts else "no evidence collected"
        if missing_dimensions:
            summary += f" | missing={','.join(missing_dimensions)}"
        if conflicts:
            summary += f" | conflicts={','.join(conflicts)}"
        return summary


class HypothesisRouter:
    AGENT_BY_TOPIC = {
        TOPIC_AI: "ai_transformation_agent",
        TOPIC_CONTRACT: "major_contract_agent",
        TOPIC_EARNINGS: "earnings_surprise_agent",
        TOPIC_MA: "ma_strategic_agent",
        TOPIC_REGULATORY: "regulatory_legal_patent_agent",
    }

    def route(self, validated: Dict[str, Any], case_data: Dict[str, Any]) -> Dict[str, Any]:
        contract = case_data.get("normalized_contract", {})
        dte = contract.get("dte") or 0
        scores = {}
        for topic, bucket in validated.get("by_hypothesis", {}).items():
            score = bucket.get("count", 0) * 3 + bucket.get("total_reliability_score", 0)
            if topic == TOPIC_EARNINGS and dte and dte <= 14:
                score += 5
            if topic == TOPIC_NOISE and abs(contract.get("underlying_move_5d") or 0) > 0.1:
                score += 3
            scores[topic] = score

        primary_topics = [
            topic for topic, _score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
            if topic != TOPIC_NOISE and _score > 0
        ][:2]
        if not primary_topics:
            primary_topics = [TOPIC_EARNINGS if dte and dte <= 14 else TOPIC_CONTRACT]

        selected_agents = ["sec_filings_agent", "public_attention_noise_agent"]
        selected_agents.extend(self.AGENT_BY_TOPIC[topic] for topic in primary_topics if self.AGENT_BY_TOPIC[topic] not in selected_agents)

        return {
            "topic_scores": scores,
            "ordered_hypotheses": primary_topics + [TOPIC_NOISE],
            "selected_agents": selected_agents,
            "summary": f"route={selected_agents} topics={primary_topics}",
        }


def format_validated_bucket(validated: Dict[str, Any], topic: str, limit: int = 5) -> str:
    bucket = (validated.get("by_hypothesis") or {}).get(topic, {})
    evidence = bucket.get("evidence", [])[:limit]
    if not evidence:
        return "No validated evidence in this topic bucket."
    lines = []
    for item in evidence:
        lines.append(
            f"- [{item.get('reliability', 'D')}] {item.get('title', '')} | "
            f"{item.get('source_name', '')} | {item.get('snippet', '')[:180]}"
        )
    return "\n".join(lines)


def format_validated_summary(validated: Dict[str, Any], limit_per_topic: int = 3) -> str:
    if not validated:
        return "No validated evidence bundle available."
    sections = [f"Missing dimensions: {validated.get('missing_dimensions', [])}"]
    for topic in HYPOTHESIS_TOPICS:
        bucket = (validated.get("by_hypothesis") or {}).get(topic, {})
        if not bucket.get("count"):
            continue
        sections.append(f"## {topic}\n{format_validated_bucket(validated, topic, limit=limit_per_topic)}")
    return "\n".join(sections)
