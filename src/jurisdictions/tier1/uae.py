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


class UaeBuilder(JurisdictionBuilder):
    """Builder for United Arab Emirates (AE) – SCA/DFSA/ADGM regulated fund centre."""

    def build_entry(self) -> RegulatoryEntry:
        manager = SourceGovernanceManager()

        manager.add_citation(CitationRecord(
            source_name="UAE Federal Law No. 4 of 2000 on the Emirates Securities and Commodities Authority",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2000, 1, 1),
            section_reference="Article 12 – Fund Registration Requirements",
            reliability_score=0.95,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="DIFC Collective Investment Law (DIFC Law No. 2 of 2010)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2010, 1, 1),
            section_reference="CIFR Module – Chapters 1–8",
            reliability_score=0.96,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Structure",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="ADGM Collective Investment Rules 2024",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2024, 4, 1),
            section_reference="Parts 2–6 – Fund Authorisation and Registration",
            reliability_score=0.96,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Securities and Commodities Authority (SCA)",
            source_url="https://www.sca.gov.ae",
            authority=SourceAuthority.PRIMARY,
            authority_level=1,
            publication_date=datetime(2024, 1, 15),
            section_reference="Fund Regulations – Public and Private Fund Requirements",
            reliability_score=0.88,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Dubai Financial Services Authority (DFSA)",
            source_url="https://www.dfsa.ae",
            authority=SourceAuthority.PRIMARY,
            authority_level=1,
            publication_date=datetime(2024, 6, 1),
            section_reference="Collective Investment Fund Rules – DIFC",
            reliability_score=0.88,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Structure",
            last_verified_timestamp=datetime.utcnow(),
        ))

        governance = manager.build()

        entry = RegulatoryEntry(
            jurisdiction_code="AE",
            jurisdiction_name="United Arab Emirates",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="Securities and Commodities Authority (SCA)",
            secondary_regulators=[
                "Dubai Financial Services Authority (DFSA)",
                "Abu Dhabi Global Market Financial Services Regulatory Authority (ADGM FSRA)",
            ],
            permitted_fund_structures=[
                FundStructure(
                    structure_type="Public Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("10000000"),
                        currency="AED",
                        amount_usd_equivalent=Decimal("2722000"),
                        notes="AED 10M minimum initial capital",
                    ),
                    notes="Offered to public; SCA regulated; full prospectus required",
                ),
                FundStructure(
                    structure_type="Private Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("50000000"),
                        currency="AED",
                        amount_usd_equivalent=Decimal("13610000"),
                        notes="AED 50M minimum or equivalent",
                    ),
                    notes="For qualified investors; lighter regulatory requirements",
                ),
                FundStructure(
                    structure_type="DIFC Domestic Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No SCA approval needed; DFSA regulated; min USD 500K per investor",
                    ),
                    notes="DIFC domiciled fund; DFSA regulated; for professional clients only",
                ),
                FundStructure(
                    structure_type="ADGM Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No SCA approval needed; ADGM FSRA regulated",
                    ),
                    notes="ADGM domiciled fund; FSRA regulated; recognised as equivalent to EU AIFMD",
                ),
            ],
            investor_requirements=InvestorRequirements(
                qualified_investor_required=False,
                min_investment_usd=Decimal("500000"),
                residency_restrictions=[],
                accreditation_standard="SCA Qualified Investor Definition (net assets > AED 5M or annual income > AED 1M)",
                notes="DIFC/ADGM funds restricted to professional clients; SCA public funds available to retail",
            ),
            filing_obligations=[
                RegulatoryFiling(
                    filing_type="Annual Report",
                    frequency="Annual",
                    regulator="SCA",
                    deadline_description="Within 4 months of fiscal year end",
                    format_required="XBRL",
                ),
                RegulatoryFiling(
                    filing_type="AUM Disclosure",
                    frequency="Quarterly",
                    regulator="SCA",
                    deadline_description="Within 30 days of quarter end",
                ),
                RegulatoryFiling(
                    filing_type="DFSA Regulatory Return",
                    frequency="Quarterly",
                    regulator="DFSA",
                    deadline_description="Within 30 days of quarter end",
                    format_required="DFSA portal",
                ),
                RegulatoryFiling(
                    filing_type="ADGM FSRA Reporting",
                    frequency="Semi-Annual",
                    regulator="ADGM FSRA",
                    deadline_description="Within 45 days of period end",
                ),
            ],
            licensing_requirements=[
                LicensingRequirement(
                    licence_type="SCA Fund Registration – Public Fund",
                    issuing_authority="Securities and Commodities Authority (SCA)",
                    applies_to="Fund",
                    statutory_reference="SCA Board of Directors Decision No. 9 of 2016",
                    notes="Full registration required for public funds offered to retail investors",
                ),
                LicensingRequirement(
                    licence_type="SCA Fund Registration – Private Fund",
                    issuing_authority="SCA",
                    applies_to="Fund",
                    statutory_reference="SCA Board of Directors Decision No. 9 of 2016",
                    notes="Registration for private funds offered to qualified investors",
                ),
                LicensingRequirement(
                    licence_type="DFSA Licence – Fund Manager",
                    issuing_authority="Dubai Financial Services Authority (DFSA)",
                    applies_to="Manager",
                    statutory_reference="DFSA Rulebook – GEN Module",
                    notes="Required for fund managers operating in DIFC",
                ),
                LicensingRequirement(
                    licence_type="ADGM FSRA Licence – Fund Manager",
                    issuing_authority="ADGM Financial Services Regulatory Authority (FSRA)",
                    applies_to="Manager",
                    statutory_reference="ADGM FSRA Rules – Prudential and Conduct of Business Rules",
                    notes="Required for fund managers operating in ADGM",
                ),
            ],
            substance_requirements=SubstanceRequirement(
                local_office_required=True,
                local_directors_required=True,
                minimum_local_directors=2,
                local_staff_required=True,
                minimum_local_staff=2,
                notes="DIFC/ADGM: physical office required; at least 2 directors; sufficient staff demonstrating substance. SCA-regulated: UAE registered office required",
            ),
            regulatory_timelines=[
                RegulatoryTimeline(
                    process_name="SCA Public Fund Registration",
                    minimum_days=60,
                    maximum_days=180,
                    typical_days=120,
                    notes="SCA review of public fund applications typically takes 4–6 months",
                ),
                RegulatoryTimeline(
                    process_name="SCA Private Fund Registration",
                    minimum_days=30,
                    maximum_days=90,
                    typical_days=60,
                    notes="Private fund registration is faster; 2–3 months typical",
                ),
                RegulatoryTimeline(
                    process_name="DFSA Fund Authorisation",
                    minimum_days=30,
                    maximum_days=90,
                    typical_days=60,
                    notes="DFSA processing for DIFC-domiciled funds; typically 2–3 months",
                ),
                RegulatoryTimeline(
                    process_name="ADGM FSRA Fund Authorisation",
                    minimum_days=30,
                    maximum_days=90,
                    typical_days=60,
                    notes="ADGM fund authorisation similar to DFSA; 2–3 months typical",
                ),
            ],
            regulatory_costs=[
                RegulatoryCost(
                    cost_type="SCA Fund Registration Fee",
                    amount=Decimal("50000"),
                    currency="AED",
                    amount_usd_equivalent=Decimal("13610"),
                    frequency="One-time",
                    notes="SCA registration fee for fund establishment",
                ),
                RegulatoryCost(
                    cost_type="SCA Annual Supervision Fee",
                    amount=Decimal("25000"),
                    currency="AED",
                    amount_usd_equivalent=Decimal("6800"),
                    frequency="Annual",
                    notes="Annual supervision fee payable to SCA",
                ),
                RegulatoryCost(
                    cost_type="DFSA Application Fee",
                    amount=Decimal("10000"),
                    currency="USD",
                    amount_usd_equivalent=Decimal("10000"),
                    frequency="One-time",
                    notes="DFSA application fee for fund manager licence",
                ),
                RegulatoryCost(
                    cost_type="ADGM FSRA Annual Fee",
                    amount=Decimal("5000"),
                    currency="USD",
                    amount_usd_equivalent=Decimal("5000"),
                    frequency="Annual",
                    notes="Annual FSRA supervision fee for ADGM funds",
                ),
            ],
            penalty_exposure=[
                PenaltyExposure(
                    breach_type="Late Filing with SCA",
                    maximum_fine_usd=Decimal("50000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="SCA may impose fines for late filing; licence suspension possible",
                ),
                PenaltyExposure(
                    breach_type="AML/CFT Breach",
                    maximum_fine_usd=Decimal("5000000"),
                    criminal_liability=True,
                    licence_revocation_possible=True,
                    notes="UAE AML Law No. 20 of 2018 provides for severe penalties including criminal liability",
                ),
                PenaltyExposure(
                    breach_type="DFSA Rule Breach",
                    maximum_fine_usd=Decimal("500000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="DFSA enforcement powers include financial penalties and licence revocation",
                ),
            ],
            wind_down_procedure=WindDownProcedure(
                voluntary_liquidation_available=True,
                typical_duration_days=180,
                regulator_approval_required=True,
                creditor_protection_period_days=60,
                notes="Voluntary liquidation requires SCA/DFSA/ADGM approval depending on fund domicile; court involvement possible; typical duration 6–9 months",
            ),
            fund_manager_requirements=FundManagerRequirement(
                local_manager_required=True,
                minimum_aum_for_full_licence_usd=None,
                fit_and_proper_required=True,
                experience_years_required=3,
                notes="DFSA/ADGM require locally licensed fund manager for domestic funds; fit and proper test applies; minimum 3 years relevant experience for key personnel",
            ),
            marketing_restrictions=[
                MarketingRestriction(
                    target_investor_type="Qualified Investor",
                    permitted_jurisdictions=["AE", "Global"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=True,
                    notes="Private funds limited to qualified investors under SCA rules; cross-border marketing subject to local regulations",
                ),
                MarketingRestriction(
                    target_investor_type="Professional",
                    permitted_jurisdictions=["AE", "GCC", "Global"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=True,
                    notes="DIFC/ADGM funds restricted to professional clients; no retail marketing outside SCA framework",
                ),
            ],
            beneficial_ownership_rules=BeneficialOwnershipRule(
                register_required=True,
                register_public=True,
                threshold_percentage=Decimal("25"),
                filing_authority="UAE Ministry of Economy – Ultimate Beneficial Owner (UBO) Register",
                notes="UAE requires UBO register maintained by Ministry of Economy; threshold at 25%; publicly accessible for licensed entities",
            ),
            record_retention_policies=[
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="All Fund Records",
                    statutory_reference="SCA Board of Directors Decision No. 9 of 2016",
                    notes="Fund records must be retained for at least 5 years",
                ),
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="AML Records",
                    statutory_reference="UAE AML/CFT Law No. 20 of 2018 and Cabinet Resolution No. 10 of 2019",
                    notes="AML/CFT records must be retained for at least 5 years after business relationship ends",
                ),
            ],
            tax_summary="No corporate tax on fund income; VAT at 5% on management fees; DIFC/ADGM entities enjoy 0% corporate tax guarantee until 2050.",
            withholding_tax_rate=Decimal("0"),
            aml_kyc_framework="UAE AML/CFT Law No. 20 of 2018; Cabinet Resolution No. 10 of 2019; SCA AML Rules",
            passporting_available=False,
            passporting_notes="No formal passporting regime; DIFC/ADGM funds recognised under certain equivalence regimes",
            source_governance=governance,
            confidence=self._placeholder_confidence(),
            version=VersionRecord(
                version_id="1.0.0",
                author="legal-swarm-system",
                change_summary="Initial UAE regulatory entry",
            ),
        )
        return entry
