from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from .common import Provenance
from .explainability import DriversSection
from .risk import ExposureSection, LiquiditySection, ModelSection

Priority = Literal["high", "medium", "low"]
IncidentStatus = Literal["active", "resolved"]
EvidenceReadinessStatus = Literal["ready", "partial", "insufficient"]
WorkflowStage = Literal["evidence_check", "response_ready_for_merchant_review"]


class IncidentWindow(BaseModel):
    start_date: date
    end_date: date
    recovery_end_date: date
    duration_days: int


class ReasonCodeInfo(BaseModel):
    code: str
    label: str
    description: str
    taxonomy_disclaimer: str


class CaseSummary(BaseModel):
    estimated_case_count: int
    method: str
    provenance: Provenance
    note: str


class EvidenceItem(BaseModel):
    category: str
    label: str
    required: bool
    available: bool
    rationale: str
    provenance: Provenance


class EvidenceReadiness(BaseModel):
    reason_code: str
    required_evidence: list[str]
    items: list[EvidenceItem]
    required_count: int
    available_count: int
    missing_evidence: list[str]
    readiness_status: EvidenceReadinessStatus
    disclaimer: str


class ScenarioContext(BaseModel):
    event_id: str
    shape: str
    severity_score: float
    affects: list[str]
    provenance: Provenance
    note: str


class IncidentSummary(BaseModel):
    incident_id: str
    merchant_id: str
    event_type: str
    status: IncidentStatus
    priority: Priority
    horizon_days: int
    window: IncidentWindow
    detected_date: date
    probability_calibrated: float
    risk_state: Literal["elevated", "normal"]
    exposure_estimate: float
    liquidity_stress: float | None
    reason_code: str
    reason_code_label: str
    evidence_readiness_status: EvidenceReadinessStatus
    estimated_case_count: int
    workflow_stage: WorkflowStage


class IncidentListResponse(BaseModel):
    merchant_id: str
    count: int
    incidents: list[IncidentSummary]


class IncidentDetail(BaseModel):
    incident_id: str
    merchant_id: str
    event_type: str
    status: IncidentStatus
    priority: Priority
    priority_reasons: list[str]
    horizon_days: int
    day_index: int
    window: IncidentWindow
    detected_date: date
    detection_note: str
    model: ModelSection
    exposure: ExposureSection
    liquidity: LiquiditySection
    drivers: DriversSection
    causality_disclaimer: str
    reason_code: ReasonCodeInfo
    case_summary: CaseSummary
    evidence_readiness: EvidenceReadiness
    scenario_context: ScenarioContext
    workflow_stage: WorkflowStage


class IncidentEvidenceResponse(BaseModel):
    incident_id: str
    merchant_id: str
    evidence_readiness: EvidenceReadiness
