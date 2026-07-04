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


class JerseyBuilder(JurisdictionBuilder):
    """Builder for Jersey (JE) – recognised international fund centre."""

    def build_entry(self) -> RegulatoryEntry:
        manager = SourceGovernanceManager()

        manager.add_citation(CitationRecord(
            source_name="Collective Investment Funds (Jersey) Law 1988",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(1988, 1, 1),
            section_reference="Articles 2–15 – Certification of Funds",
            reliability_score=0.95,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Alternative Investment Funds (Jersey) Regulations 2012",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2012, 1, 1),
            section_reference="Parts 2–5 – Authorisation and Registration",
            reliability_score=0.95,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Jersey Financial Services Commission",
            source_url="https://www.jerseyfsc.org",
            authority=SourceAuthority.PRIMARY,
            authority_level=1,
            publication_date=datetime(2024, 1, 1),
            section_reference="Funds Handbook 2024 – Chapters 1–6",
            reliability_score=0.90,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Ogier – Jersey Fund Formation Guide",
            source_url="https://www.ogier.com",
            authority=SourceAuthority.SECONDARY,
            authority_level=4,
            publication_date=datetime(2024, 6, 1),
            section_reference="Fund Types and Regulatory Requirements",
            reliability_score=0.80,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Structure",
            last_verified_timestamp=datetime.utcnow(),
        ))

        governance = manager.build()

        entry = RegulatoryEntry(
            jurisdiction_code="JE",
            jurisdiction_name="Jersey",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="Jersey Financial Services Commission (JFSC)",
            secondary_regulators=["Jersey Revenue Service", "Jersey Financial Crime Unit"],
            permitted_fund_structures=[
                FundStructure(
                    structure_type="Expert Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No minimum capital; min investment USD 100,000 (or equivalent) per investor",
                    ),
                    notes="Fast-track 48-hour certification; for professional and expert investors; most common Jersey fund structure",
                ),
                FundStructure(
                    structure_type="Listed Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No minimum capital; must be listed on recognised stock exchange",
                    ),
                    notes="Certified fund listed on CISX or other recognised exchange; full JFSC authorisation",
                ),
                FundStructure(
                    structure_type="Unclassified Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("1000000"),
                        currency="USD",
                        amount_usd_equivalent=Decimal("1000000"),
                        notes="USD 1M minimum; for retail investors",
                    ),
                    notes="Full JFSC authorisation; available to retail investors; most regulated category",
                ),
                FundStructure(
                    structure_type="Incorporated Cell Company (ICC)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No separate minimum for individual cells",
                    ),
                    notes="Each cell treated separately; protected cell regime; flexible umbrella structure",
                ),
            ],
            investor_requirements=InvestorRequirements(
                qualified_investor_required=False,
                min_investment_usd=None,
                residency_restrictions=[],
                accreditation_standard="Expert Fund: investor must be 'expert' (min USD 100K investment or net worth > USD 1M)",
                notes="Unclassified funds available to retail; Expert Funds restricted to expert investors; Listed Funds publicly traded",
            ),
            filing_obligations=[
                RegulatoryFiling(
                    filing_type="Annual Return",
                    frequency="Annual",
                    regulator="JFSC",
                    deadline_description="Within 6 months of fiscal year end",
                    format_required="JFSC prescribed form",
                ),
                RegulatoryFiling(
                    filing_type="Audited Financial Statements",
                    frequency="Annual",
                    regulator="JFSC",
                    deadline_description="Within 6 months of fiscal year end",
                    format_required="Audited by JFSC-approved auditor",
                ),
                RegulatoryFiling(
                    filing_type="Material Change Notification",
                    frequency="Ad-hoc",
                    regulator="JFSC",
                    deadline_description="Immediately upon occurrence",
                ),
                RegulatoryFiling(
                    filing_type="AIFMD Equivalent Reporting",
                    frequency="Annual",
                    regulator="JFSC",
                    deadline_description="Within 45 days of year end",
                ),
            ],
            licensing_requirements=[
                LicensingRequirement(
                    licence_type="Expert Fund Certification",
                    issuing_authority="Jersey Financial Services Commission (JFSC)",
                    applies_to="Fund",
                    statutory_reference="Collective Investment Funds (Jersey) Law 1988, Article 4",
                    notes="Fast-track 48-hour certification for expert funds; most common Jersey fund structure",
                ),
                LicensingRequirement(
                    licence_type="Listed Fund Certification",
                    issuing_authority="JFSC",
                    applies_to="Fund",
                    statutory_reference="Collective Investment Funds (Jersey) Law 1988, Article 7",
                    notes="Certification for funds listed on recognised stock exchange",
                ),
                LicensingRequirement(
                    licence_type="Unclassified Fund Authorisation",
                    issuing_authority="JFSC",
                    applies_to="Fund",
                    statutory_reference="Collective Investment Funds (Jersey) Law 1988, Article 3",
                    notes="Full JFSC authorisation for retail funds; most regulated category",
                ),
                LicensingRequirement(
                    licence_type="Jersey AIFM Licence",
                    issuing_authority="JFSC",
                    applies_to="Manager",
                    statutory_reference="Alternative Investment Funds (Jersey) Regulations 2012",
                    notes="Required for alternative investment fund managers operating in Jersey",
                ),
            ],
            substance_requirements=SubstanceRequirement(
                local_office_required=True,
                local_directors_required=True,
                minimum_local_directors=2,
                local_staff_required=False,
                minimum_local_staff=None,
                notes="Must have registered office in Jersey; at least 2 Jersey-resident directors required; sufficient substance expected per JFSC guidance",
            ),
            regulatory_timelines=[
                RegulatoryTimeline(
                    process_name="Expert Fund Certification",
                    minimum_days=1,
                    maximum_days=3,
                    typical_days=2,
                    notes="JFSC 48-hour fast-track certification for expert funds",
                ),
                RegulatoryTimeline(
                    process_name="Unclassified Fund Authorisation",
                    minimum_days=30,
                    maximum_days=90,
                    typical_days=60,
                    notes="Full JFSC authorisation for unclassified funds; typically 2–3 months",
                ),
                RegulatoryTimeline(
                    process_name="AIFM Licence Application",
                    minimum_days=60,
                    maximum_days=180,
                    typical_days=120,
                    notes="JFSC review of AIFM licence applications; typically 3–6 months",
                ),
            ],
            regulatory_costs=[
                RegulatoryCost(
                    cost_type="Expert Fund Certification Fee",
                    amount=Decimal("2500"),
                    currency="GBP",
                    amount_usd_equivalent=Decimal("3200"),
                    frequency="Annual",
                    notes="Annual JFSC fee for expert fund certification",
                ),
                RegulatoryCost(
                    cost_type="Unclassified Fund Authorisation Fee",
                    amount=Decimal("5000"),
                    currency="GBP",
                    amount_usd_equivalent=Decimal("6400"),
                    frequency="Annual",
                    notes="Annual JFSC fee for unclassified fund authorisation",
                ),
                RegulatoryCost(
                    cost_type="AIFM Licence Fee",
                    amount=Decimal("10000"),
                    currency="GBP",
                    amount_usd_equivalent=Decimal("12800"),
                    frequency="Annual",
                    notes="Annual JFSC fee for AIFM licence",
                ),
                RegulatoryCost(
                    cost_type="Jersey GST (5% on management fees)",
                    amount=Decimal("0"),
                    currency="GBP",
                    amount_usd_equivalent=Decimal("0"),
                    frequency="Annual",
                    notes="GST at 5% applies to management and administration fees",
                ),
            ],
            penalty_exposure=[
                PenaltyExposure(
                    breach_type="Late Annual Return Filing",
                    maximum_fine_usd=Decimal("50000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="JFSC may impose fines and ultimately revoke certification for persistent non-compliance",
                ),
                PenaltyExposure(
                    breach_type="AML/CFT Breach",
                    maximum_fine_usd=Decimal("1000000"),
                    criminal_liability=True,
                    licence_revocation_possible=True,
                    notes="Criminal penalties under Proceeds of Crime (Jersey) Law 1999",
                ),
                PenaltyExposure(
                    breach_type="Breach of Fund Rules",
                    maximum_fine_usd=Decimal("100000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="JFSC enforcement powers include fines and suspension of certification",
                ),
            ],
            wind_down_procedure=WindDownProcedure(
                voluntary_liquidation_available=True,
                typical_duration_days=90,
                regulator_approval_required=True,
                creditor_protection_period_days=30,
                notes="Voluntary liquidation requires JFSC approval; creditor notification required; typical duration 3–6 months",
            ),
            fund_manager_requirements=FundManagerRequirement(
                local_manager_required=False,
                minimum_aum_for_full_licence_usd=Decimal("100000000"),
                fit_and_proper_required=True,
                experience_years_required=5,
                notes="Non-Jersey AIFMs authorised under AIFMD equivalence regime; Jersey AIFMs require JFSC licence if managing > EUR 100M AUM; fit and proper test",
            ),
            marketing_restrictions=[
                MarketingRestriction(
                    target_investor_type="Expert",
                    permitted_jurisdictions=["Global"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=True,
                    notes="Expert funds limited to expert investors (min USD 100K investment or net worth > USD 1M); global distribution with local restrictions",
                ),
                MarketingRestriction(
                    target_investor_type="Retail",
                    permitted_jurisdictions=["JE", "GB"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=False,
                    notes="Unclassified funds available to retail investors; subject to local securities laws in each jurisdiction",
                ),
            ],
            beneficial_ownership_rules=BeneficialOwnershipRule(
                register_required=True,
                register_public=False,
                threshold_percentage=Decimal("25"),
                filing_authority="Jersey Financial Services Commission (JFSC) – Central Register of Beneficial Ownership",
                notes="Jersey central register of beneficial ownership maintained by JFSC; not publicly accessible; threshold at 25%; law enforcement access only",
            ),
            record_retention_policies=[
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="All Fund Records",
                    statutory_reference="Collective Investment Funds (Jersey) Law 1988",
                    notes="Fund records must be retained for at least 5 years",
                ),
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="AML Records",
                    statutory_reference="Money Laundering (Jersey) Order 2008",
                    notes="AML/CFT records must be retained for at least 5 years after business relationship ends",
                ),
            ],
            tax_summary="0% corporate income tax on fund income. No withholding tax on distributions. No capital gains tax. GST at 5% applies to management fees. Annual JFSC fee applies.",
            withholding_tax_rate=Decimal("0"),
            aml_kyc_framework="Proceeds of Crime (Jersey) Law 1999; Money Laundering (Jersey) Order 2008; JFSC AML Handbook 2023",
            passporting_available=False,
            passporting_notes="No EU passporting; Jersey is a third-country jurisdiction; deemed equivalent under AIFMD for non-EU AIFs",
            source_governance=governance,
            confidence=self._placeholder_confidence(),
            version=VersionRecord(
                version_id="1.0.0",
                author="legal-swarm-system",
                change_summary="Initial Jersey regulatory entry",
            ),
        )
        return entry
