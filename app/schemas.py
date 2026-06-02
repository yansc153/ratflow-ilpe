from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class OptionAlertInput(BaseModel):
    source: str = "manual"
    ticker: str
    company_name: Optional[str] = None
    option_type: str = Field(..., pattern="^(CALL|PUT)$")
    strike: float
    expiry: str
    dte: Optional[int] = None
    volume: int
    open_interest: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    last_price: Optional[float] = None
    implied_volatility: Optional[float] = None
    iv_change: Optional[float] = None
    premium: Optional[float] = None
    underlying_price: Optional[float] = None
    underlying_move_5d: Optional[float] = None
    raw_text: Optional[str] = None


class OptionAlertResponse(BaseModel):
    id: int
    case_id: int
    source: str
    ticker: str
    option_type: str
    strike: float
    expiry: str
    dte: Optional[int] = None
    volume: int
    open_interest: int
    volume_oi_ratio: Optional[float] = None
    implied_volatility: Optional[float] = None
    premium: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CaseResponse(BaseModel):
    id: int
    case_uid: str
    status: str
    ticker: str
    company_name: Optional[str] = None
    direction: Optional[str] = None
    main_contract_label: Optional[str] = None
    source: Optional[str] = None
    research_depth: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CaseDetailResponse(CaseResponse):
    alert: Optional[OptionAlertResponse] = None
    leakage_report: Optional[Dict[str, Any]] = None


class AgentRunResponse(BaseModel):
    id: int
    agent_name: str
    status: str
    output_json: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EvidenceItemResponse(BaseModel):
    id: int
    agent_name: str
    evidence_type: Optional[str] = None
    evidence_quality: Optional[str] = None
    polarity: Optional[str] = None
    title: Optional[str] = None
    source_name: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None
    relevance_score: Optional[float] = None

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: int
    case_id: int
    leakage_score: Optional[float] = None
    tradeability_score: Optional[float] = None
    model_estimated_profit_probability: Optional[float] = None
    calibration_confidence: Optional[str] = None
    calibration_grade: Optional[str] = None
    event_probabilities_json: Optional[Dict[str, Any]] = None
    trade_suggestion_json: Optional[Dict[str, Any]] = None
    report_markdown: Optional[str] = None
    discord_message_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OIConfirmationResponse(BaseModel):
    id: int
    case_id: int
    old_oi: Optional[int] = None
    new_oi: Optional[int] = None
    oi_change: Optional[int] = None
    oi_confirmation_ratio: Optional[float] = None
    status: Optional[str] = None
    old_leakage_score: Optional[float] = None
    new_leakage_score: Optional[float] = None
    checked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OutcomeResponse(BaseModel):
    id: int
    case_id: int
    horizon: str
    underlying_return: Optional[float] = None
    option_estimated_return: Optional[float] = None
    max_favorable_excursion: Optional[float] = None
    max_adverse_excursion: Optional[float] = None
    event_confirmed: Optional[str] = None
    event_type_confirmed: Optional[str] = None
    failure_reason: Optional[str] = None
    checked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CalibrationStats(BaseModel):
    total_cases: int
    cases_with_outcomes: int
    calibration_grade: str
    avg_leakage_score: Optional[float] = None
    avg_profit_probability: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class DiscordTestResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
