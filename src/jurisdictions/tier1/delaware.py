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


class DelawareBuilder(JurisdictionBuilder):
    """Builder for Delaware (US) – primary US hedge fund domicile with SEC/CFTC oversight."""

    def build_entry(self) -> RegulatoryEntry:
        manager = SourceGovernanceManager()

        manager.add_citation(CitationRecord(
            source_name="Investment Company Act of 1940 (United States)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(1940, 8, 22),
            section_reference="Sections 3(c)(1) and 3(c)(7) – Hedge Fund Exemptions from Registration",
            reliability_score=0.98,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Investment Advisers Act of 1940 (United States)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(1940, 8, 22),
            section_reference="Section 203(m) – Private Fund Adviser Exemption",
            reliability_score=0.98,
            raw_excerpt=None,
            regulatory_relevance_tag="Licensing",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Delaware Revised Uniform Limited Partnership Act (Title 6, Chapter 17)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2024, 1, 1),
            section_reference="Chapter 17 – Limited Partnerships Formation and Operation",
            reliability_score=0.97,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Structure",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Securities and Exchange Commission (SEC)",
            source_url="https://www.sec.gov",
            authority=SourceAuthority.PRIMARY,
            authority_level=1,
            publication_date=datetime(2024, 1, 1),
            section_reference="Investment Adviser Registration and Reporting – Form ADV, Form PF",
            reliability_score=0.92,
            raw_excerpt=None,
            regulatory_relevance_tag="Licensing",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Commodity Futures Trading Commission (CFTC)",
            source_url="https://www.cftc.gov",
            authority=SourceAuthority.PRIMARY,
            authority_level=1,
            publication_date=datetime(2024, 1, 1),
            section_reference="Regulations 4.5, 4.7, 4.13 – Private Fund Exemptions",
            reliability_score=0.90,
            raw_excerpt=None,
            regulatory_relevance_tag="Licensing",
            last_verified_timestamp=datetime.utcnow(),
        ))

        governance = manager.build()

        entry = RegulatoryEntry(
            jurisdiction_code="US-DE",
            jurisdiction_name="Delaware (United States)",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="Securities and Exchange Commission (SEC)",
            secondary_regulators=[
                "Commodity Futures Trading Commission (CFTC)",
                "Financial Industry Regulatory Authority (FINRA)",
                "Delaware Division of Corporations",
            ],
            permitted_fund_structures=[
                FundStructure(
                    structure_type="Delaware Limited Partnership (LP)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No federal or Delaware statutory minimum for private funds",
                    ),
                    notes="Most common hedge fund structure; governed by Delaware Revised Uniform Limited Partnership Act",
                ),
                FundStructure(
                    structure_type="Delaware Limited Liability Company (LLC)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No statutory minimum capital",
                    ),
                    notes="Alternative to LP; more flexible governance; single-member LLC possible",
                ),
                FundStructure(
                    structure_type="Private Fund (3(c)(1) or 3(c)(7))",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No minimum capital; 100-investor limit for 3(c)(1); qualified purchasers for 3(c)(7)",
                    ),
                    notes="Exempt from Investment Company Act registration; most common for hedge funds; accredited investors required",
                ),
                FundStructure(
                    structure_type="Registered Investment Company (RIC)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("100000"),
                        currency="USD",
                        amount_usd_equivalent=Decimal("100000"),
                        notes="Market practice minimum; no statutory minimum for incorporated entity",
                    ),
                    notes="Fully SEC-registered under Investment Company Act 1940; available to retail investors",
                ),
            ],
            investor_requirements=InvestorRequirements(
                qualified_investor_required=False,
                min_investment_usd=None,
                residency_restrictions=[],
                accreditation_standard="Accredited Investor (SEC Rule 501 of Reg D): net worth > USD 1M (excl. primary residence) or income > USD 200K (USD 300K joint)",
                notes="3(c)(7) funds require 'qualified purchasers' (USD 5M+ investable assets); non-US investors may invest under Regulation S",
            ),
            filing_obligations=[
                RegulatoryFiling(
                    filing_type="Form ADV (Investment Adviser Registration)",
                    frequency="Annual",
                    regulator="SEC",
                    deadline_description="Within 90 days of fiscal year end",
                    format_required="IARD electronic filing",
                ),
                RegulatoryFiling(
                    filing_type="Form PF (Private Fund Reporting)",
                    frequency="Quarterly",
                    regulator="SEC",
                    deadline_description="Within 60 days of quarter end (large hedge funds) or 120 days (mid-size)",
                    format_required="XML via SEC portal",
                ),
                RegulatoryFiling(
                    filing_type="Form 13F (Institutional Holdings)",
                    frequency="Quarterly",
                    regulator="SEC",
                    deadline_description="Within 45 days of quarter end",
                    format_required="Electronic via EDGAR",
                ),
                RegulatoryFiling(
                    filing_type="Form D (Regulation D Exemption Notice)",
                    frequency="Upon offering",
                    regulator="SEC",
                    deadline_description="Within 15 days of first sale",
                    format_required="Electronic via EDGAR",
                ),
                RegulatoryFiling(
                    filing_type="Delaware Annual Report",
                    frequency="Annual",
                    regulator="Delaware Division of Corporations",
                    deadline_description="By 1 March each year",
                    format_required="Online via Delaware Corp portal",
                ),
            ],
    licensing_requirements=[
        LicensingRequirement(
            licence_type="SEC Registration – Investment Adviser",
            issuing_authority="Securities and Exchange Commission (SEC)",
            applies_to="Manager",
            statutory_reference="Investment Advisers Act of 1940, Section 203",
            notes="Required for advisers managing > USD 100M AUM; registration via Form ADV",
        ),
        LicensingRequirement(
            licence_type="State Registration – Investment Adviser",
            issuing_authority="State Securities Regulators",
            applies_to="Manager",
            statutory_reference="Investment Advisers Act of 1940, Section 203A",
            notes="Required for advisers managing < USD 100M AUM; registration in home state",
        ),
        LicensingRequirement(
            licence_type="CFTC Registration – Commodity Pool Operator (CPO)",
            issuing_authority="Commodity Futures Trading Commission (CFTC)",
            applies_to="Manager",
            statutory_reference="Commodity Exchange Act, Section 4m",
            notes="Required if fund trades commodity interests; exemptions available under Reg 4.5, 4.7, 4.13",
        ),
    ],
    substance_requirements=SubstanceRequirement(
        local_office_required=False,
        local_directors_required=False,
        minimum_local_directors=None,
        local_staff_required=False,
        minimum_local_staff=None,
        notes="Delaware does not impose substance requirements on limited partnerships or LLCs. Funds generally managed from outside Delaware; no local office, directors, or staff required",
    ),
    regulatory_timelines=[
        RegulatoryTimeline(
            process_name="Form ADV Registration (SEC)",
            minimum_days=30,
            maximum_days=60,
            typical_days=45,
            notes="SEC typically processes Form ADV within 45 days from filing",
        ),
        RegulatoryTimeline(
            process_name="Delaware LP/LLC Formation",
            minimum_days=1,
            maximum_days=5,
            typical_days=2,
            notes="Delaware Division of Corporations processes filings within 1–3 business days; same-day expedited available",
        ),
        RegulatoryTimeline(
            process_name="Form D Filing (Regulation D)",
            minimum_days=1,
            maximum_days=1,
            typical_days=1,
            notes="Form D must be filed within 15 days of first sale; filing is electronic and processed same day",
        ),
    ],
    regulatory_costs=[
        RegulatoryCost(
            cost_type="Delaware LP Formation Fee",
            amount=Decimal("200"),
            currency="USD",
            amount_usd_equivalent=Decimal("200"),
            frequency="One-time",
            notes="State filing fee for Certificate of Limited Partnership",
        ),
        RegulatoryCost(
            cost_type="Delaware LLC Formation Fee",
            amount=Decimal("90"),
            currency="USD",
            amount_usd_equivalent=Decimal("90"),
            frequency="One-time",
            notes="State filing fee for Certificate of Formation",
        ),
        RegulatoryCost(
            cost_type="Delaware Annual Franchise Tax (LP)",
            amount=Decimal("300"),
            currency="USD",
            amount_usd_equivalent=Decimal("300"),
            frequency="Annual",
            notes="Minimum annual franchise tax for limited partnerships",
        ),
        RegulatoryCost(
            cost_type="Delaware Annual Franchise Tax (LLC)",
            amount=Decimal("300"),
            currency="USD",
            amount_usd_equivalent=Decimal("300"),
            frequency="Annual",
            notes="Minimum annual franchise tax for LLCs",
        ),
        RegulatoryCost(
            cost_type="SEC Registration Fee (Form ADV)",
            amount=Decimal("225"),
            currency="USD",
            amount_usd_equivalent=Decimal("225"),
            frequency="Annual",
            notes="Annual SEC fee for investment adviser registration",
        ),
    ],
    penalty_exposure=[
        PenaltyExposure(
            breach_type="Late Form ADV Filing",
            maximum_fine_usd=Decimal("50000"),
            criminal_liability=False,
            licence_revocation_possible=True,
            notes="SEC may impose fines and suspend registration for late or inaccurate ADV filings",
        ),
        PenaltyExposure(
            breach_type="Form PF Late Filing",
            maximum_fine_usd=Decimal("100000"),
            criminal_liability=False,
            licence_revocation_possible=True,
            notes="SEC enforcement for late or inaccurate Form PF submissions",
        ),
        PenaltyExposure(
            breach_type="AML/BSA Breach",
            maximum_fine_usd=Decimal("10000000"),
            criminal_liability=True,
            licence_revocation_possible=True,
            notes="BSA/AML violations subject to severe civil and criminal penalties; FinCEN and SEC enforcement",
        ),
        PenaltyExposure(
            breach_type="Securities Fraud",
            maximum_fine_usd=Decimal("5000000"),
            criminal_liability=True,
            licence_revocation_possible=True,
            notes="SEC enforcement for fraudulent activities; criminal liability under Securities Act 1933 and Exchange Act 1934",
        ),
    ],
    wind_down_procedure=WindDownProcedure(
        voluntary_liquidation_available=True,
        typical_duration_days=60,
        regulator_approval_required=False,
        creditor_protection_period_days=30,
        notes="Delaware LPs and LLCs can be voluntarily dissolved without SEC approval; Certificate of Cancellation filed with Delaware Division of Corporations; creditor notification required",
    ),
    fund_manager_requirements=FundManagerRequirement(
        local_manager_required=False,
        minimum_aum_for_full_licence_usd=Decimal("100000000"),
        fit_and_proper_required=True,
        experience_years_required=None,
        notes="No Delaware residency requirement for fund manager; SEC registration threshold at USD 100M AUM for hedge fund advisers; Form ADV disclosing disciplinary history",
    ),
    marketing_restrictions=[
        MarketingRestriction(
            target_investor_type="Accredited",
            permitted_jurisdictions=["US"],
            restricted_jurisdictions=[],
            pre_marketing_allowed=True,
            notes="Regulation D Rule 506(b): unlimited accredited investors, up to 35 non-accredited; no general solicitation",
        ),
        MarketingRestriction(
            target_investor_type="Qualified Purchaser",
            permitted_jurisdictions=["US"],
            restricted_jurisdictions=[],
            pre_marketing_allowed=True,
            notes="3(c)(7) funds: unlimited qualified purchasers (USD 5M+ investable assets); general solicitation allowed under Rule 506(c)",
        ),
        MarketingRestriction(
            target_investor_type="Non-US",
            permitted_jurisdictions=["Global"],
            restricted_jurisdictions=[],
            pre_marketing_allowed=True,
            notes="Regulation S offshore offerings: no registration required for non-US investors; no directed selling efforts in US",
        ),
    ],
    beneficial_ownership_rules=BeneficialOwnershipRule(
        register_required=True,
        register_public=False,
        threshold_percentage=Decimal("25"),
        filing_authority="Financial Crimes Enforcement Network (FinCEN) – Corporate Transparency Act (CTA)",
        notes="Corporate Transparency Act effective 2024: beneficial ownership reporting to FinCEN; register not publicly accessible; threshold at 25%; substantial penalties for non-compliance",
    ),
    record_retention_policies=[
        RecordRetentionPolicy(
            minimum_retention_years=5,
            applies_to="All Fund Records",
            statutory_reference="Investment Advisers Act of 1940, Rule 204-2",
            notes="SEC Rule 204-2: records must be retained for at least 5 years (first 2 years on premises)",
        ),
        RecordRetentionPolicy(
            minimum_retention_years=5,
            applies_to="AML Records",
            statutory_reference="Bank Secrecy Act; FinCEN regulations",
            notes="AML records must be retained for at least 5 years under BSA requirements",
        ),
        RecordRetentionPolicy(
            minimum_retention_years=6,
            applies_to="Form PF and Compliance Records",
            statutory_reference="SEC Rules 204(b)-1 and 206(4)-7",
            notes="Form PF records and compliance documentation retained for 6 years",
        ),
    ],
            tax_summary="No Delaware state income tax for LLCs/LPs. Federal corporate income tax at 21%. Withholding tax at 30% on certain US-source income for non-US investors (treaty rates may apply). Interest and dividends taxable to investors.",
            withholding_tax_rate=Decimal("30"),
            aml_kyc_framework="Bank Secrecy Act (BSA); USA PATRIOT Act; FINRA AML Rules; SEC AML compliance requirements for registered advisers",
            passporting_available=False,
            passporting_notes="No passporting; SEC-registered advisers can market to accredited investors across all US states under Regulation D",
            source_governance=governance,
            confidence=self._placeholder_confidence(),
            version=VersionRecord(
                version_id="1.0.0",
                author="legal-swarm-system",
                change_summary="Initial Delaware (US) regulatory entry",
            ),
        )
        return entry
