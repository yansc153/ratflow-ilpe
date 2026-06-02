from typing import Dict, Any, List, Optional
from app.logging_config import logger


class ScoringEngine:
    @staticmethod
    def compute_leakage_score(
        options_dna: Dict[str, Any],
        evidence_strength: float,
        noise_score: float,
        price_lag_score: float,
        oi_quality_score: float,
        historical_similarity: float,
    ) -> float:
        components = {
            "options_dna": (options_dna.get("options_dna_score", 0) or 0) * 0.30,
            "evidence_strength": evidence_strength * 0.25,
            "noise_silence": (100 - noise_score) * 0.15,
            "price_lag": price_lag_score * 0.10,
            "oi_quality": oi_quality_score * 0.10,
            "historical_similarity": historical_similarity * 0.10,
        }
        total = sum(components.values())
        return round(min(100, max(0, total)), 1)

    @staticmethod
    def compute_tradeability_score(
        spread_quality: float,
        iv_reasonableness: float,
        liquidity_score: float,
        time_to_event: float,
        price_lag: float,
        contract_quality_score: float,
        oi_confirmed: bool,
    ) -> float:
        components = {
            "spread_quality": spread_quality * 0.20,
            "iv_reasonableness": iv_reasonableness * 0.15,
            "liquidity": liquidity_score * 0.15,
            "time_to_event": time_to_event * 0.15,
            "price_lag": price_lag * 0.15,
            "contract_quality": contract_quality_score * 0.10,
            "oi_confirmed": (25 if oi_confirmed else 0) * 0.10,
        }
        total = sum(components.values())
        return round(min(100, max(0, total)), 1)

    @staticmethod
    def compute_noise_score(
        public_news_exists: bool,
        social_heat: float,
        stock_runup: float,
        earnings_proximity: bool,
        iv_extreme: bool,
        spread_terrible: bool,
    ) -> float:
        score = 0.0
        if public_news_exists:
            score += 25
        score += social_heat * 25
        score += stock_runup * 20
        if earnings_proximity:
            score += 15
        if iv_extreme:
            score += 10
        if spread_terrible:
            score += 5
        return round(min(100, max(0, score)), 1)
