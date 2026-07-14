"""
Master Canonical Schema — Legal Swarm Regulatory Intelligence System
=====================================================================
Defines the authoritative data models for all regulatory intelligence
objects. All agents, validators, and output layers must conform to
these schemas. No schema drift or undocumented deviation is permitted.

Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ConfidenceLevel(str, Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"
    UNVERIFIED = "UNVERIFIED"


class JurisdictionTier(str, Enum):
    TIER_1 = "TIER_1"   # Primary execution baseline
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"


class SourceAuthority(str, Enum):
    PRIMARY    = "PRIMARY"    # Official government / regulator publication
    SECONDARY  = "SECONDARY"  # Recognized legal commentary / analysis
    TERTIARY   = "TERTIARY"   # General reference


class ChangeType(str, Enum):
    ADDED    = "ADDED"
    MODIFIED = "MODIFIED"
    REMOVED  = "REMOVED"
    UNCHANGED = "UNCHANGED"


class ValidationStatus(str, Enum):
    PASSED  = "PASSED"
    FAILED  = "FAILED"
    WARNING = "WARNING"
    PENDING = "PENDING"


class NotApplicableReason(str, Enum):
    NO_REGULATORY_REQUIREMENT = "NO_REGULATORY_REQUIREMENT"
    JURISDICTION_EXEMPT        = "JURISDICTION_EXEMPT"
    NOT_YET_VERIFIED           = "NOT_YET_VERIFIED"
    OUTSIDE_CURRENT_SCOPE      = "OUTSIDE_CURRENT_SCOPE"


class AuditEventType(str, Enum):
    QUERY              = "QUERY"
    VALIDATION         = "VALIDATION"
    CONTRADICTION      = "CONTRADICTION"
    CONFIDENCE_DECISION = "CONFIDENCE_DECISION"
    SCHEMA_UPDATE      = "SCHEMA_UPDATE"
    SOURCE_INGESTION   = "SOURCE_INGESTION"
    DELTA_DETECTED     = "DELTA_DETECTED"


# ---------------------------------------------------------------------------
# Source Governance
# ---------------------------------------------------------------------------

class CitationRecord(BaseModel):
    """Single authoritative citation backing a regulatory claim."""

    citation_id: UUID = Field(default_factory=uuid4)
    authority_id: str | None = Field(None, description="Reference to an Authority in the Authority Registry")
    source_name: str = Field(..., min_length=1, description="Name of the source document or publication")
    source_url: str | None = Field(None, description="Direct URL to the source if available")
    authority: SourceAuthority
    authority_level: int = Field(
        default=2,
        ge=1,
        le=5,
        description=(
            "SRS authority level 1-5: "
            "1=Official regulator website, "
            "2=Statutory legislation database, "
            "3=Government gazette, "
            "4=Recognized legal firm, "
            "5=Professional advisory firm"
        ),
    )
    publication_date: datetime | None = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    section_reference: str | None = Field(None, description="Section, article, or clause reference within the source")
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Reliability score between 0 and 1")
    raw_excerpt: str | None = Field(None, description="Verbatim excerpt from source (max 2000 chars)")
    regulatory_relevance_tag: str | None = Field(
        None,
        description="Regulatory area this citation covers e.g. 'Fund Registration', 'AML/CFT', 'Capital Requirements'",
    )
    last_verified_timestamp: datetime | None = Field(
        None,
        description="Timestamp when this citation was last verified as current and accurate",
    )

    @field_validator("raw_excerpt")
    @classmethod
    def cap_excerpt_length(cls, v: str | None) -> str | None:
        if v and len(v) > 2000:
            raise ValueError("raw_excerpt must not exceed 2000 characters")
        return v


class SourceGovernanceRecord(BaseModel):
    """Tracks source hierarchy and authority for a regulatory entry."""

    primary_citations: list[CitationRecord] = Field(default_factory=list)
    secondary_citations: list[CitationRecord] = Field(default_factory=list)
    tertiary_citations: list[CitationRecord] = Field(default_factory=list)
    dominant_source: SourceAuthority = Field(
        default=SourceAuthority.PRIMARY,
        description="Highest-authority source tier present"
    )

    @model_validator(mode="after")
    def at_least_one_citation(self) -> SourceGovernanceRecord:
        total = (
            len(self.primary_citations)
            + len(self.secondary_citations)
            + len(self.tertiary_citations)
        )
        if total == 0:
            raise ValueError("At least one citation is required per regulatory entry")
        return self

    @model_validator(mode="after")
    def derive_dominant_source(self) -> SourceGovernanceRecord:
        if self.primary_citations:
            self.dominant_source = SourceAuthority.PRIMARY
        elif self.secondary_citations:
            self.dominant_source = SourceAuthority.SECONDARY
        elif self.tertiary_citations:
            self.dominant_source = SourceAuthority.TERTIARY
        return self


# ---------------------------------------------------------------------------
# Capital & Cost Normalization
# ---------------------------------------------------------------------------

class CapitalRequirement(BaseModel):
    """Normalized capital / cost figure across jurisdictions."""

    amount: Decimal | None = Field(None, description="Numeric amount in normalized currency")
    currency: str = Field("USD", min_length=3, max_length=3, description="ISO 4217 currency code")
    amount_usd_equivalent: Decimal | None = Field(None, description="USD equivalent at time of ingestion")
    notes: str | None = Field(None, description="Qualitative notes where numeric normalization is not possible")


# ---------------------------------------------------------------------------
# Confidence Scoring
# ---------------------------------------------------------------------------

class ConfidenceScore(BaseModel):
    """Structured confidence assessment for a regulatory data point."""

    level: ConfidenceLevel
    score: float = Field(..., ge=0.0, le=1.0, description="Numeric confidence 0–1")
    rationale: str = Field(..., min_length=1, description="Explanation of confidence determination")
    contributing_factors: list[str] = Field(default_factory=list)
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Contradiction Detection
# ---------------------------------------------------------------------------

class ContradictionRecord(BaseModel):
    """Records a detected contradiction between regulatory data points."""

    contradiction_id: UUID = Field(default_factory=uuid4)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    field_path: str = Field(..., description="Dot-notation path to the contradicting field, e.g. 'fund_structures.min_capital'")
    source_a: CitationRecord
    source_b: CitationRecord
    value_a: str = Field(..., description="Value from source A (serialized as string)")
    value_b: str = Field(..., description="Value from source B (serialized as string)")
    resolution: str | None = Field(None, description="Resolution note if contradiction was resolved")
    resolved: bool = False


# ---------------------------------------------------------------------------
# Validation Framework
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    """Result of a single validation check against the schema."""

    rule_id: str = Field(..., description="Unique identifier for the validation rule")
    rule_description: str
    status: ValidationStatus
    field_path: str | None = None
    message: str | None = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationReport(BaseModel):
    """Aggregated validation report for a regulatory entry."""

    report_id: UUID = Field(default_factory=uuid4)
    entry_id: UUID
    jurisdiction_code: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    results: list[ValidationResult] = Field(default_factory=list)
    overall_status: ValidationStatus = ValidationStatus.PENDING
    schema_version: str = Field(..., description="Schema version this report was validated against")

    @model_validator(mode="after")
    def compute_overall_status(self) -> ValidationReport:
        if not self.results:
            return self
        statuses = {r.status for r in self.results}
        if ValidationStatus.FAILED in statuses:
            self.overall_status = ValidationStatus.FAILED
        elif ValidationStatus.WARNING in statuses:
            self.overall_status = ValidationStatus.WARNING
        else:
            self.overall_status = ValidationStatus.PASSED
        return self


# ---------------------------------------------------------------------------
# Versioning & Delta Tracking
# ---------------------------------------------------------------------------

class FieldDelta(BaseModel):
    """Records a change to a single field between versions."""

    field_path: str
    change_type: ChangeType
    old_value: Any | None = None
    new_value: Any | None = None


class VersionRecord(BaseModel):
    """Version metadata and delta log for a regulatory entry."""

    version_id: str = Field(..., description="Semantic version string, e.g. '1.0.0'")
    previous_version_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    author: str | None = Field(None, description="Agent or user that produced this version")
    change_summary: str | None = None
    deltas: list[FieldDelta] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------

class AuditLogEntry(BaseModel):
    """Immutable audit log record. Must never be modified after creation."""

    log_id: UUID = Field(default_factory=uuid4)
    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str = Field(..., description="Agent ID, user ID, or system process that triggered the event")
    jurisdiction_code: str | None = None
    entry_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-specific structured data")
    outcome: str | None = None

    model_config = {"frozen": True}  # Enforce immutability at model level


# ---------------------------------------------------------------------------
# Core Regulatory Entry — Master Canonical Schema
# ---------------------------------------------------------------------------

class FundStructure(BaseModel):
    """Permissible fund structures and associated capital requirements."""

    structure_type: str = Field(..., description="e.g. 'Open-Ended', 'Closed-Ended', 'UCITS', 'AIF'")
    is_permitted: bool
    min_capital: CapitalRequirement | None = None
    max_leverage_ratio: float | None = Field(None, ge=0.0)
    notes: str | None = None


class InvestorRequirements(BaseModel):
    """Investor eligibility and qualification rules."""

    qualified_investor_required: bool = True
    min_investment_usd: Decimal | None = None
    residency_restrictions: list[str] = Field(default_factory=list, description="ISO 3166-1 alpha-2 country codes")
    accreditation_standard: str | None = None
    notes: str | None = None


class RegulatoryFiling(BaseModel):
    """Filing and reporting obligations."""

    filing_type: str = Field(..., description="e.g. 'Annual Report', 'AUM Disclosure', 'Risk Report'")
    frequency: str = Field(..., description="e.g. 'Annual', 'Quarterly', 'Monthly'")
    regulator: str
    deadline_description: str | None = None
    format_required: str | None = None


# ---------------------------------------------------------------------------
# Licensing Requirements
# ---------------------------------------------------------------------------

class LicensingRequirement(BaseModel):
    """A specific licence required to operate a fund or management entity."""

    licence_type: str = Field(..., description="Name of the licence required, e.g. 'SIBL Licence', 'RFMC Licence'")
    issuing_authority: str = Field(..., description="Regulatory body that issues the licence")
    applies_to: str = Field(..., description="Who needs it: 'Fund', 'Manager', or 'Both'")
    statutory_reference: str | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Substance Requirements
# ---------------------------------------------------------------------------

class SubstanceRequirement(BaseModel):
    """Local substance / economic presence rules."""

    local_office_required: bool
    local_directors_required: bool
    minimum_local_directors: int | None = None
    local_staff_required: bool
    minimum_local_staff: int | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Regulatory Timelines
# ---------------------------------------------------------------------------

class RegulatoryTimeline(BaseModel):
    """Expected processing timeline for a regulatory process."""

    process_name: str = Field(..., description="e.g. 'Fund Registration', 'Manager Licensing'")
    minimum_days: int | None = None
    maximum_days: int | None = None
    typical_days: int | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Regulatory Costs
# ---------------------------------------------------------------------------

class RegulatoryCost(BaseModel):
    """A cost or fee imposed by the regulator or service providers."""

    cost_type: str = Field(..., description="e.g. 'Formation Fee', 'Annual Regulator Fee', 'Audit Fee'")
    amount: Decimal | None = None
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    amount_usd_equivalent: Decimal | None = None
    frequency: str = Field(..., description="e.g. 'One-time', 'Annual'")
    notes: str | None = None


# ---------------------------------------------------------------------------
# Penalty Exposures
# ---------------------------------------------------------------------------

class PenaltyExposure(BaseModel):
    """Penalties and sanctions for regulatory breaches."""

    breach_type: str = Field(..., description="e.g. 'Late Filing', 'AML Breach', 'Unauthorised Activity'")
    maximum_fine_usd: Decimal | None = None
    criminal_liability: bool = False
    licence_revocation_possible: bool = False
    notes: str | None = None


# ---------------------------------------------------------------------------
# Wind-Down Procedures
# ---------------------------------------------------------------------------

class WindDownProcedure(BaseModel):
    """Rules and timelines for winding down a fund."""

    voluntary_liquidation_available: bool = True
    typical_duration_days: int | None = None
    regulator_approval_required: bool = True
    creditor_protection_period_days: int | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Fund Manager Requirements
# ---------------------------------------------------------------------------

class FundManagerRequirement(BaseModel):
    """Requirements for the fund manager entity."""

    local_manager_required: bool = True
    minimum_aum_for_full_licence_usd: Decimal | None = None
    fit_and_proper_required: bool = True
    experience_years_required: int | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Marketing Restrictions
# ---------------------------------------------------------------------------

class MarketingRestriction(BaseModel):
    """Rules governing who and where fund shares may be marketed."""

    target_investor_type: str = Field(..., description="e.g. 'Retail', 'Professional', 'Accredited'")
    permitted_jurisdictions: list[str] = Field(default_factory=list, description="ISO 3166-1 alpha-2 codes or ['Global']")
    restricted_jurisdictions: list[str] = Field(default_factory=list)
    pre_marketing_allowed: bool = False
    notes: str | None = None


# ---------------------------------------------------------------------------
# Beneficial Ownership Rules
# ---------------------------------------------------------------------------

class BeneficialOwnershipRule(BaseModel):
    """Disclosure and register requirements for beneficial owners."""

    register_required: bool = True
    register_public: bool = False
    threshold_percentage: Decimal | None = Field(None, description="Ownership percentage triggering disclosure")
    filing_authority: str | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Record Retention Policies
# ---------------------------------------------------------------------------

class RecordRetentionPolicy(BaseModel):
    """Mandatory record-keeping periods."""

    minimum_retention_years: int = Field(..., ge=1, le=50)
    applies_to: str = Field(..., description="e.g. 'All Fund Records', 'AML Records', 'Transaction Records'")
    statutory_reference: str | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Core Regulatory Entry — Master Canonical Schema
# ---------------------------------------------------------------------------

class RegulatoryEntry(BaseModel):
    """
    Master canonical regulatory record for a single jurisdiction.
    This is the top-level schema unit — all agents read and write this type.
    """

    entry_id: UUID = Field(default_factory=uuid4)
    jurisdiction_code: str = Field(..., min_length=2, max_length=10, description="ISO 3166-1 or custom jurisdiction code")
    jurisdiction_name: str = Field(..., min_length=1)
    tier: JurisdictionTier

    # Regulatory body
    primary_regulator: str = Field(..., description="Name of the primary regulatory authority")
    secondary_regulators: list[str] = Field(default_factory=list)

    # Fund structures
    permitted_fund_structures: list[FundStructure] = Field(default_factory=list)

    # Investor requirements
    investor_requirements: InvestorRequirements | None = None

    # Filing obligations
    filing_obligations: list[RegulatoryFiling] = Field(default_factory=list)

    # Licensing
    licensing_requirements: list[LicensingRequirement] | None = None

    # Substance
    substance_requirements: SubstanceRequirement | None = None

    # Regulatory timelines
    regulatory_timelines: list[RegulatoryTimeline] | None = None

    # Regulatory costs
    regulatory_costs: list[RegulatoryCost] | None = None

    # Penalties
    penalty_exposure: list[PenaltyExposure] | None = None

    # Wind-down
    wind_down_procedure: WindDownProcedure | None = None

    # Fund manager requirements
    fund_manager_requirements: FundManagerRequirement | None = None

    # Marketing restrictions
    marketing_restrictions: list[MarketingRestriction] | None = None

    # Beneficial ownership
    beneficial_ownership_rules: BeneficialOwnershipRule | None = None

    # Record retention
    record_retention_policies: list[RecordRetentionPolicy] | None = None

    # Taxation summary
    tax_summary: str | None = Field(None, description="High-level tax treatment narrative")
    withholding_tax_rate: Decimal | None = Field(None, ge=Decimal("0"), le=Decimal("100"))

    # AML / KYC
    aml_kyc_framework: str | None = None

    # Passporting / equivalence
    passporting_available: bool = False
    passporting_notes: str | None = None

    # Governance
    source_governance: SourceGovernanceRecord

    # Confidence
    confidence: ConfidenceScore

    # Contradictions detected
    contradictions: list[ContradictionRecord] = Field(default_factory=list)

    # Versioning
    version: VersionRecord

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated_at: datetime = Field(default_factory=datetime.utcnow)
    next_review_due: datetime | None = None

    # Schema version this entry conforms to
    schema_version: str = Field(default="1.0.0")

    @field_validator("jurisdiction_code")
    @classmethod
    def normalize_jurisdiction_code(cls, v: str) -> str:
        return v.upper().strip()

    @model_validator(mode="after")
    def confidence_threshold_gate(self) -> RegulatoryEntry:
        """Reject entries that fall below minimum confidence threshold."""
        if self.confidence.score < 0.4 and self.confidence.level != ConfidenceLevel.UNVERIFIED:
            raise ValueError(
                f"Confidence score {self.confidence.score} is below the 0.4 minimum threshold. "
                "Mark as UNVERIFIED or improve source quality."
            )
        return self


# ---------------------------------------------------------------------------
# Cross-Jurisdiction Comparison
# ---------------------------------------------------------------------------

class JurisdictionComparisonField(BaseModel):
    """A single normalized field extracted for cross-jurisdiction comparison."""

    field_name: str
    jurisdiction_code: str
    value: Any
    confidence: ConfidenceScore


class CrossJurisdictionComparison(BaseModel):
    """Structured comparison result across multiple jurisdictions."""

    comparison_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    jurisdictions: list[str] = Field(..., min_length=2, description="Jurisdiction codes being compared")
    fields_compared: list[str]
    results: list[JurisdictionComparisonField] = Field(default_factory=list)
    contradictions_detected: list[ContradictionRecord] = Field(default_factory=list)
    summary: str | None = None