import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db import Base


def generate_uid():
    return uuid.uuid4().hex[:12].upper()


class InvestigationCase(Base):
    __tablename__ = "investigation_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_uid = Column(String(24), unique=True, nullable=False, default=generate_uid)
    status = Column(String(50), nullable=False, default="NEW")
    ticker = Column(String(10), nullable=False, index=True)
    company_name = Column(String(200), nullable=True)
    direction = Column(String(20), nullable=True)
    main_contract_label = Column(String(200), nullable=True)
    source = Column(String(50), nullable=True)
    data_quality = Column(String(20), nullable=True, default="unknown")
    research_depth = Column(String(20), nullable=True, default="none")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    alert = relationship("OptionAlert", back_populates="case", uselist=False)
    agent_runs = relationship("AgentRun", back_populates="case")
    evidence_items = relationship("EvidenceItem", back_populates="case")
    leakage_report = relationship("LeakageReport", back_populates="case", uselist=False)
    oi_confirmations = relationship("OIConfirmation", back_populates="case")
    outcomes = relationship("Outcome", back_populates="case")
    state_transitions = relationship("CaseStateTransition", back_populates="case")


class OptionAlert(Base):
    __tablename__ = "option_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id"), unique=True, nullable=False)
    source = Column(String(50), nullable=False)
    ticker = Column(String(10), nullable=False)
    company_name = Column(String(200), nullable=True)
    option_type = Column(String(4), nullable=False)
    strike = Column(Float, nullable=False)
    expiry = Column(String(10), nullable=False)
    dte = Column(Integer, nullable=True)
    volume = Column(Integer, nullable=False)
    open_interest = Column(Integer, nullable=False)
    volume_oi_ratio = Column(Float, nullable=True)
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    last_price = Column(Float, nullable=True)
    mid_price = Column(Float, nullable=True)
    implied_volatility = Column(Float, nullable=True)
    iv_change = Column(Float, nullable=True)
    premium = Column(Float, nullable=True)
    underlying_price = Column(Float, nullable=True)
    underlying_move_1d = Column(Float, nullable=True)
    underlying_move_5d = Column(Float, nullable=True)
    raw_text = Column(Text, nullable=True)
    raw_json = Column(JSON, nullable=True)
    collected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("InvestigationCase", back_populates="alert")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id"), nullable=False)
    alert_id = Column(Integer, ForeignKey("option_alerts.id"), nullable=True)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    input_json = Column(JSON, nullable=True)
    output_json = Column(JSON, nullable=True)
    evidence_json = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    case = relationship("InvestigationCase", back_populates="agent_runs")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    evidence_type = Column(String(50), nullable=True)
    evidence_quality = Column(String(2), nullable=True)
    polarity = Column(String(20), nullable=True)
    title = Column(String(500), nullable=True)
    source_name = Column(String(200), nullable=True)
    url = Column(Text, nullable=True)
    published_at = Column(String(50), nullable=True)
    snippet = Column(Text, nullable=True)
    relevance_score = Column(Float, nullable=True, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("InvestigationCase", back_populates="evidence_items")


class LeakageReport(Base):
    __tablename__ = "leakage_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id"), unique=True, nullable=False)
    alert_id = Column(Integer, ForeignKey("option_alerts.id"), nullable=True)
    leakage_score = Column(Float, nullable=True)
    tradeability_score = Column(Float, nullable=True)
    model_estimated_profit_probability = Column(Float, nullable=True)
    calibration_confidence = Column(String(20), nullable=True)
    calibration_grade = Column(String(20), nullable=True)
    event_probabilities_json = Column(JSON, nullable=True)
    option_dna_json = Column(JSON, nullable=True)
    research_evidence_json = Column(JSON, nullable=True)
    noise_risks_json = Column(JSON, nullable=True)
    trade_suggestion_json = Column(JSON, nullable=True)
    report_markdown = Column(Text, nullable=True)
    discord_message_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("InvestigationCase", back_populates="leakage_report")


class OIConfirmation(Base):
    __tablename__ = "oi_confirmations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id"), nullable=False)
    alert_id = Column(Integer, ForeignKey("option_alerts.id"), nullable=True)
    old_oi = Column(Integer, nullable=True)
    new_oi = Column(Integer, nullable=True)
    alert_day_volume = Column(Integer, nullable=True)
    oi_change = Column(Integer, nullable=True)
    oi_confirmation_ratio = Column(Float, nullable=True)
    status = Column(String(30), nullable=True)
    old_leakage_score = Column(Float, nullable=True)
    new_leakage_score = Column(Float, nullable=True)
    score_delta = Column(Float, nullable=True)
    checked_at = Column(DateTime, nullable=True)

    case = relationship("InvestigationCase", back_populates="oi_confirmations")


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id"), nullable=False)
    alert_id = Column(Integer, ForeignKey("option_alerts.id"), nullable=True)
    horizon = Column(String(10), nullable=False)
    underlying_return = Column(Float, nullable=True)
    option_estimated_return = Column(Float, nullable=True)
    max_favorable_excursion = Column(Float, nullable=True)
    max_adverse_excursion = Column(Float, nullable=True)
    event_confirmed = Column(String(20), nullable=True)
    event_type_confirmed = Column(String(100), nullable=True)
    failure_reason = Column(String(100), nullable=True)
    checked_at = Column(DateTime, nullable=True)

    case = relationship("InvestigationCase", back_populates="outcomes")


class CaseStateTransition(Base):
    __tablename__ = "case_state_transitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id"), nullable=False)
    from_status = Column(String(50), nullable=False)
    to_status = Column(String(50), nullable=False)
    reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("InvestigationCase", back_populates="state_transitions")
