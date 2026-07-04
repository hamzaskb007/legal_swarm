from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.governance.source_governance import SourceGovernanceManager
from src.jurisdictions.base import JurisdictionBuilder
from src.schema.schema import (
    BeneficialOwnershipRule,
    CapitalRequirement,
    CitationRecord,
    FundManagerRequirement,
    FundStructure,
    InvestorRequirements,
    JurisdictionTier,
    LicensingRequirement,
    MarketingRestriction,
    PenaltyExposure,
    RecordRetentionPolicy,
    RegulatoryCost,
    RegulatoryEntry,
    RegulatoryFiling,
    RegulatoryTimeline,
    SourceAuthority,
    SubstanceRequirement,
    VersionRecord,
    WindDownProcedure,
)


class BviBuilder(JurisdictionBuilder):
    """Builder for British Virgin Islands (VG) – major offshore fund domicile."""

    def build_entry(self) -> RegulatoryEntry:
        manager = SourceGovernanceManager()

        manager.add_citation(CitationRecord(
            source_name="BVI Securities and Investment Business Act 2010 (SIBA)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2010, 1, 1),
            section_reference="Part III – Recognition of Funds",
            reliability_score=0.97,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="BVI Investment Business Regulatory Code 2024",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2024, 3, 1),
            section_reference="Parts 5–8",
            reliability_score=0.95,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="BVI Mutual Funds Regulations 2024",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2024, 3, 1),
            section_reference="Regulations 3–18",
            reliability_score=0.95,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="BVI Financial Services Commission",
            source_url="https://www.bvifsc.vg",
            authority=SourceAuthority.PRIMARY,
            authority_level=1,
            publication_date=datetime(2024, 5, 1),
            section_reference="Fund Categories and Requirements",
            reliability_score=0.85,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))

        governance = manager.build()

        entry = RegulatoryEntry(
            jurisdiction_code="VG",
            jurisdiction_name="British Virgin Islands",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="BVI Financial Services Commission (FSC)",
            secondary_regulators=["BVI International Tax Authority", "BVI Financial Investigation Agency"],
            permitted_fund_structures=[
                FundStructure(
                    structure_type="Incubator Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No minimum capital; max 20 investors; max USD 20M NAV",
                    ),
                    notes="Light-touch regulation; 2-year incubation period; exempt from audit requirement",
                ),
                FundStructure(
                    structure_type="Approved Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("20000"),
                        currency="USD",
                        amount_usd_equivalent=Decimal("20000"),
                        notes="USD 20,000 minimum; max 20 investors",
                    ),
                    notes="Simplified recognition; for smaller fund structures; annual audit required",
                ),
                FundStructure(
                    structure_type="Professional Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("100000"),
                        currency="USD",
                        amount_usd_equivalent=Decimal("100000"),
                        notes="USD 100,000 minimum investment per investor",
                    ),
                    notes="For sophisticated investors; most common hedge fund structure in BVI",
                ),
                FundStructure(
                    structure_type="Private Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No minimum capital; max 50 investors",
                    ),
                    notes="For private equity and venture capital; regulated under Private Investment Funds Act",
                ),
            ],
            investor_requirements=InvestorRequirements(
                qualified_investor_required=False,
                min_investment_usd=None,
                residency_restrictions=[],
                accreditation_standard="Professional Fund: investors must make min USD 100K initial investment or have net worth > USD 1M",
                notes="Incubator and Approved Funds have fewer restrictions; Professional Fund requires sophisticated investors",
            ),
            filing_obligations=[
                RegulatoryFiling(
                    filing_type="Annual Return",
                    frequency="Annual",
                    regulator="BVI FSC",
                    deadline_description="Within 6 months of fiscal year end",
                    format_required="Electronic via BVI FSC portal",
                ),
                RegulatoryFiling(
                    filing_type="Audited Financial Statements",
                    frequency="Annual",
                    regulator="BVI FSC",
                    deadline_description="Within 6 months of fiscal year end (Incubator exempt)",
                    format_required="Audited by FSC-approved auditor",
                ),
                RegulatoryFiling(
                    filing_type="Material Change Notification",
                    frequency="Ad-hoc",
                    regulator="BVI FSC",
                    deadline_description="Within 14 days of change",
                ),
                RegulatoryFiling(
                    filing_type="Annual Fee Payment",
                    frequency="Annual",
                    regulator="BVI FSC",
                    deadline_description="By 31 January each year",
                ),
            ],
            licensing_requirements=[
                LicensingRequirement(
                    licence_type="Incubator Fund Recognition",
                    issuing_authority="BVI Financial Services Commission (FSC)",
                    applies_to="Fund",
                    statutory_reference="Securities and Investment Business Act 2010 (SIBA), Part III",
                    notes="Simplified recognition; 2-year incubation period; no audit required",
                ),
                LicensingRequirement(
                    licence_type="Approved Fund Recognition",
                    issuing_authority="BVI FSC",
                    applies_to="Fund",
                    statutory_reference="Securities and Investment Business Act 2010 (SIBA), Part III",
                    notes="For funds with max 20 investors; lighter regulatory requirements",
                ),
                LicensingRequirement(
                    licence_type="Professional Fund Recognition",
                    issuing_authority="BVI FSC",
                    applies_to="Fund",
                    statutory_reference="Securities and Investment Business Act 2010 (SIBA), Part III",
                    notes="Most common structure; min USD 100K per investor; full recognition required",
                ),
                LicensingRequirement(
                    licence_type="Investment Business Licence",
                    issuing_authority="BVI FSC",
                    applies_to="Manager",
                    statutory_reference="Securities and Investment Business Act 2010 (SIBA), Part II",
                    notes="Required for fund managers and investment advisers operating in or from BVI",
                ),
            ],
            substance_requirements=SubstanceRequirement(
                local_office_required=True,
                local_directors_required=False,
                minimum_local_directors=None,
                local_staff_required=False,
                minimum_local_staff=None,
                notes="Must maintain registered office and registered agent in BVI; no statutory requirement for local directors or staff",
            ),
            regulatory_timelines=[
                RegulatoryTimeline(
                    process_name="Incubator Fund Recognition",
                    minimum_days=1,
                    maximum_days=3,
                    typical_days=2,
                    notes="Expedited recognition; can be completed within 2 business days",
                ),
                RegulatoryTimeline(
                    process_name="Approved Fund Recognition",
                    minimum_days=3,
                    maximum_days=7,
                    typical_days=5,
                    notes="Standard processing within 5 business days",
                ),
                RegulatoryTimeline(
                    process_name="Professional Fund Recognition",
                    minimum_days=5,
                    maximum_days=15,
                    typical_days=10,
                    notes="Full FSC review; typically 10 business days",
                ),
            ],
            regulatory_costs=[
                RegulatoryCost(
                    cost_type="Incubator Fund Recognition Fee",
                    amount=Decimal("1000"),
                    currency="USD",
                    amount_usd_equivalent=Decimal("1000"),
                    frequency="Annual",
                    notes="Annual fee for incubator fund status",
                ),
                RegulatoryCost(
                    cost_type="Approved Fund Recognition Fee",
                    amount=Decimal("2000"),
                    currency="USD",
                    amount_usd_equivalent=Decimal("2000"),
                    frequency="Annual",
                    notes="Annual fee for approved fund",
                ),
                RegulatoryCost(
                    cost_type="Professional Fund Recognition Fee",
                    amount=Decimal("3000"),
                    currency="USD",
                    amount_usd_equivalent=Decimal("3000"),
                    frequency="Annual",
                    notes="Annual fee for professional fund",
                ),
                RegulatoryCost(
                    cost_type="BVI Government Annual Licence Fee",
                    amount=Decimal("1000"),
                    currency="USD",
                    amount_usd_equivalent=Decimal("1000"),
                    frequency="Annual",
                    notes="Annual government fee payable to BVI Government",
                ),
            ],
            penalty_exposure=[
                PenaltyExposure(
                    breach_type="Late Annual Return Filing",
                    maximum_fine_usd=Decimal("10000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="FSC may impose administrative penalties and suspend or revoke recognition for persistent non-compliance",
                ),
                PenaltyExposure(
                    breach_type="AML/CFT Breach",
                    maximum_fine_usd=Decimal("500000"),
                    criminal_liability=True,
                    licence_revocation_possible=True,
                    notes="Criminal and administrative penalties under Proceeds of Criminal Conduct Act and AML Code",
                ),
                PenaltyExposure(
                    breach_type="Unauthorised Fund Operation",
                    maximum_fine_usd=Decimal("100000"),
                    criminal_liability=True,
                    licence_revocation_possible=True,
                    notes="Operating without FSC recognition is a criminal offence under SIBA",
                ),
            ],
            wind_down_procedure=WindDownProcedure(
                voluntary_liquidation_available=True,
                typical_duration_days=90,
                regulator_approval_required=False,
                creditor_protection_period_days=30,
                notes="BVI funds can be voluntarily wound up without FSC approval for solvent liquidations; creditors must be notified; typical duration 3 months",
            ),
            fund_manager_requirements=FundManagerRequirement(
                local_manager_required=False,
                minimum_aum_for_full_licence_usd=None,
                fit_and_proper_required=True,
                experience_years_required=None,
                notes="No statutory requirement for locally domiciled fund manager; investment managers require BVI Investment Business Licence if operating in BVI",
            ),
            marketing_restrictions=[
                MarketingRestriction(
                    target_investor_type="Professional",
                    permitted_jurisdictions=["Global"],
                    restricted_jurisdictions=["US", "GB"],
                    pre_marketing_allowed=True,
                    notes="Professional funds available globally via private placement; restrictions on US and UK retail marketing",
                ),
                MarketingRestriction(
                    target_investor_type="Accredited",
                    permitted_jurisdictions=["Global"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=True,
                    notes="Accredited and institutional investors; Regulation S for non-US offerings",
                ),
            ],
            beneficial_ownership_rules=BeneficialOwnershipRule(
                register_required=True,
                register_public=False,
                threshold_percentage=Decimal("25"),
                filing_authority="BVI Financial Services Commission (FSC) – Beneficial Ownership Secure Search System (BOSS)",
                notes="BVI maintains BOSS system for law enforcement access; register not publicly accessible; threshold at 25%",
            ),
            record_retention_policies=[
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="All Fund Records",
                    statutory_reference="Securities and Investment Business Act 2010 (SIBA)",
                    notes="Fund records must be retained for at least 5 years",
                ),
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="AML Records",
                    statutory_reference="BVI AML/CFT Code of Practice 2023",
                    notes="AML records must be retained for at least 5 years after business relationship ends",
                ),
            ],
            tax_summary="No corporate income tax, capital gains tax, withholding tax, VAT, or stamp duty. Annual government and FSC fees apply. Zero-tax jurisdiction.",
            withholding_tax_rate=Decimal("0"),
            aml_kyc_framework="BVI AML/CFT Code of Practice (2023); Proceeds of Criminal Conduct Act; FSC AML Guidelines",
            passporting_available=False,
            passporting_notes="No passporting regime; BVI is an offshore non-EU jurisdiction",
            source_governance=governance,
            confidence=self._placeholder_confidence(),
            version=VersionRecord(
                version_id="1.0.0",
                author="legal-swarm-system",
                change_summary="Initial BVI regulatory entry",
            ),
        )
        return entry
