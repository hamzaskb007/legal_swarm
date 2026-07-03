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


class SingaporeBuilder(JurisdictionBuilder):
    """Builder for Singapore (SG) – MAS-regulated fund hub with VCC framework."""

    def build_entry(self) -> RegulatoryEntry:
        manager = SourceGovernanceManager()

        manager.add_citation(CitationRecord(
            source_name="Securities and Futures Act 2001 (Cap. 289, Singapore)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            publication_date=datetime(2001, 10, 1),
            section_reference="Division 2 – Collective Investment Schemes, Section 286",
            reliability_score=0.97,
            raw_excerpt=None,
        ))
        manager.add_citation(CitationRecord(
            source_name="Variable Capital Companies Act 2018 (Singapore)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            publication_date=datetime(2018, 10, 1),
            section_reference="Parts 4–7 – Registration and Operations",
            reliability_score=0.96,
            raw_excerpt=None,
        ))
        manager.add_citation(CitationRecord(
            source_name="Monetary Authority of Singapore",
            source_url="https://www.mas.gov.sg",
            authority=SourceAuthority.PRIMARY,
            publication_date=datetime(2024, 6, 1),
            section_reference="Code on Collective Investment Schemes – Chapters 1–8",
            reliability_score=0.90,
            raw_excerpt=None,
        ))
        manager.add_citation(CitationRecord(
            source_name="Accounting and Corporate Regulatory Authority (ACRA)",
            source_url="https://www.acra.gov.sg",
            authority=SourceAuthority.PRIMARY,
            publication_date=datetime(2024, 9, 1),
            section_reference="VCC Registration Requirements",
            reliability_score=0.85,
            raw_excerpt=None,
        ))

        governance = manager.build()

        entry = RegulatoryEntry(
            jurisdiction_code="SG",
            jurisdiction_name="Singapore",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="Monetary Authority of Singapore (MAS)",
            secondary_regulators=[
                "Accounting and Corporate Regulatory Authority (ACRA)",
                "Inland Revenue Authority of Singapore (IRAS)",
            ],
            permitted_fund_structures=[
                FundStructure(
                    structure_type="Variable Capital Company (VCC)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("250000"),
                        currency="SGD",
                        amount_usd_equivalent=Decimal("185000"),
                        notes="SGD 250,000 minimum initial capital; must have a Singapore-based fund manager",
                    ),
                    notes="Corporate structure for collective investment schemes; umbrella fund with multiple sub-funds; regulated under VCC Act 2018",
                ),
                FundStructure(
                    structure_type="Authorised CIS",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("1000000"),
                        currency="SGD",
                        amount_usd_equivalent=Decimal("740000"),
                        notes="SGD 1M minimum for authorised schemes offered to retail investors",
                    ),
                    notes="Full MAS authorisation; available to retail investors; regulated under SFA",
                ),
                FundStructure(
                    structure_type="Restricted CIS",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("100000"),
                        currency="SGD",
                        amount_usd_equivalent=Decimal("74000"),
                        notes="SGD 100,000 minimum investment per investor",
                    ),
                    notes="For accredited investors only; faster time-to-market; regulated under SFA",
                ),
                FundStructure(
                    structure_type="Limited Partnership (LP)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="SGD",
                        notes="No statutory minimum capital",
                    ),
                    notes="Common for private equity and venture capital; governed by Limited Partnerships Act",
                ),
            ],
            investor_requirements=InvestorRequirements(
                qualified_investor_required=False,
                min_investment_usd=None,
                residency_restrictions=[],
                accreditation_standard="Accredited investor: net personal assets > SGD 2M or income > SGD 300K p.a.",
                notes="Retail funds require full MAS authorisation; restricted schemes limited to accredited/institutional investors",
            ),
            filing_obligations=[
                RegulatoryFiling(
                    filing_type="Annual Return",
                    frequency="Annual",
                    regulator="ACRA",
                    deadline_description="Within 7 months of fiscal year end",
                    format_required="Electronic via ACRA BizFile+",
                ),
                RegulatoryFiling(
                    filing_type="Audited Financial Statements",
                    frequency="Annual",
                    regulator="MAS",
                    deadline_description="Within 5 months of fiscal year end",
                    format_required="Audited by MAS-appointed auditor",
                ),
                RegulatoryFiling(
                    filing_type="Capital Adequacy Return",
                    frequency="Quarterly",
                    regulator="MAS",
                    deadline_description="Within 15 days of quarter end",
                    format_required="MAS prescribed template",
                ),
                RegulatoryFiling(
                    filing_type="CIS Operations Report",
                    frequency="Quarterly",
                    regulator="MAS",
                    deadline_description="Within 30 days of quarter end",
                ),
            ],
            licensing_requirements=[
                LicensingRequirement(
                    licence_type="Capital Markets Services (CMS) Licence – Fund Management",
                    issuing_authority="Monetary Authority of Singapore (MAS)",
                    applies_to="Manager",
                    statutory_reference="Securities and Futures Act (Cap. 289), Section 86",
                    notes="Required for fund managers operating in Singapore; licensed under SFA",
                ),
                LicensingRequirement(
                    licence_type="Registered Fund Management Company (RFMC)",
                    issuing_authority="MAS",
                    applies_to="Manager",
                    statutory_reference="Securities and Futures Act (Cap. 289), Section 99",
                    notes="For smaller fund managers (< SGD 250M AUM); lighter regulatory regime",
                ),
                LicensingRequirement(
                    licence_type="VCC Registration",
                    issuing_authority="ACRA",
                    applies_to="Fund",
                    statutory_reference="Variable Capital Companies Act 2018, Part 4",
                    notes="Registration with ACRA required for all VCCs",
                ),
            ],
            substance_requirements=SubstanceRequirement(
                local_office_required=True,
                local_directors_required=True,
                minimum_local_directors=2,
                local_staff_required=True,
                minimum_local_staff=2,
                notes="MAS requires fund managers to have a substantive local presence: registered office, at least 2 local directors (Singapore residents), and at least 2 full-time staff",
            ),
            regulatory_timelines=[
                RegulatoryTimeline(
                    process_name="CMS Licence Application",
                    minimum_days=120,
                    maximum_days=240,
                    typical_days=180,
                    notes="MAS review typically takes 4–6 months for CMS licence applications",
                ),
                RegulatoryTimeline(
                    process_name="RFMC Registration",
                    minimum_days=60,
                    maximum_days=120,
                    typical_days=90,
                    notes="Streamlined registration process; 2–4 months for RFMC status",
                ),
                RegulatoryTimeline(
                    process_name="VCC Registration",
                    minimum_days=14,
                    maximum_days=30,
                    typical_days=21,
                    notes="ACRA VCC registration typically completed within 3 weeks",
                ),
            ],
            regulatory_costs=[
                RegulatoryCost(
                    cost_type="CMS Licence Application Fee",
                    amount=Decimal("5000"),
                    currency="SGD",
                    amount_usd_equivalent=Decimal("3700"),
                    frequency="One-time",
                    notes="MAS application fee for CMS licence for fund management",
                ),
                RegulatoryCost(
                    cost_type="MAS Annual Regulatory Fee",
                    amount=Decimal("4000"),
                    currency="SGD",
                    amount_usd_equivalent=Decimal("3000"),
                    frequency="Annual",
                    notes="Annual MAS regulatory fee for licensed fund managers",
                ),
                RegulatoryCost(
                    cost_type="VCC Registration Fee",
                    amount=Decimal("3000"),
                    currency="SGD",
                    amount_usd_equivalent=Decimal("2200"),
                    frequency="One-time",
                    notes="ACRA registration fee for VCC incorporation",
                ),
            ],
            penalty_exposure=[
                PenaltyExposure(
                    breach_type="Late Filing with ACRA",
                    maximum_fine_usd=Decimal("50000"),
                    criminal_liability=False,
                    licence_revocation_possible=False,
                    notes="Late filing penalties imposed by ACRA; administrative fines",
                ),
                PenaltyExposure(
                    breach_type="AML/CFT Breach",
                    maximum_fine_usd=Decimal("1000000"),
                    criminal_liability=True,
                    licence_revocation_possible=True,
                    notes="MAS enforcement for AML breaches; criminal penalties under CDSA",
                ),
                PenaltyExposure(
                    breach_type="Conduct of Business Breach",
                    maximum_fine_usd=Decimal("250000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="MAS may impose financial penalties and revoke CMS licence for serious breaches",
                ),
            ],
            wind_down_procedure=WindDownProcedure(
                voluntary_liquidation_available=True,
                typical_duration_days=120,
                regulator_approval_required=True,
                creditor_protection_period_days=30,
                notes="Voluntary winding up of VCC requires MAS approval and ACRA filing; creditors notified; typical completion 3–6 months",
            ),
            fund_manager_requirements=FundManagerRequirement(
                local_manager_required=True,
                minimum_aum_for_full_licence_usd=Decimal("185000000"),
                fit_and_proper_required=True,
                experience_years_required=5,
                notes="Full CMS licence required for AUM > SGD 250M; RFMC for smaller AUM; MAS fit and proper criteria apply to all key personnel; minimum 5 years relevant experience",
            ),
            marketing_restrictions=[
                MarketingRestriction(
                    target_investor_type="Accredited",
                    permitted_jurisdictions=["Global"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=True,
                    notes="Restricted schemes limited to accredited and institutional investors under SFA",
                ),
                MarketingRestriction(
                    target_investor_type="Retail",
                    permitted_jurisdictions=["SG"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=False,
                    notes="Retail CIS requires full MAS authorisation; prospectus registration required",
                ),
            ],
            beneficial_ownership_rules=BeneficialOwnershipRule(
                register_required=True,
                register_public=True,
                threshold_percentage=Decimal("25"),
                filing_authority="Accounting and Corporate Regulatory Authority (ACRA)",
                notes="ACRA central register of controllers; publicly accessible; threshold at 25% ownership; under Companies Act",
            ),
            record_retention_policies=[
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="All Fund Records",
                    statutory_reference="Securities and Futures Act (Cap. 289), Section 172",
                    notes="Fund records must be retained for at least 5 years under SFA",
                ),
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="AML Records",
                    statutory_reference="MAS Notice SFA 04-N02",
                    notes="AML/CFT records must be retained for at least 5 years after transaction or account closure",
                ),
            ],
            tax_summary="Fund-level tax exemption for approved VCC and CIS funds under Section 13R/13X of Income Tax Act. GST exemption for fund management services. No capital gains tax.",
            withholding_tax_rate=Decimal("0"),
            aml_kyc_framework="MAS Notice SFA 04-N02 – AML/CFT Requirements; Corruption, Drug Trafficking and other Serious Crimes Act (CDSA)",
            passporting_available=False,
            passporting_notes="No formal passporting regime; ASEAN cross-border recognition under development",
            source_governance=governance,
            confidence=self._placeholder_confidence(),
            version=VersionRecord(
                version_id="1.0.0",
                author="legal-swarm-system",
                change_summary="Initial Singapore regulatory entry",
            ),
        )
        return entry
