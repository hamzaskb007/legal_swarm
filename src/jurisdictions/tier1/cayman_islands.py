from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.governance.source_governance import SourceGovernanceManager
from src.jurisdictions.base import JurisdictionBuilder
from src.schema.schema import (
    BeneficialOwnershipRule,
    CapitalRequirement,
    CitationRecord,
    FundStructure,
    FundManagerRequirement,
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


class CaymanIslandsBuilder(JurisdictionBuilder):
    """Builder for Cayman Islands (KY) – the world's leading hedge fund domicile."""

    def build_entry(self) -> RegulatoryEntry:
        manager = SourceGovernanceManager()

        manager.add_citation(CitationRecord(
            source_name="Cayman Islands Mutual Funds Act (2021 Revision)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            publication_date=datetime(2021, 1, 1),
            section_reference="Part I, Sections 4–6 – Registration Requirements",
            reliability_score=0.97,
            raw_excerpt=None,
        ))
        manager.add_citation(CitationRecord(
            source_name="Cayman Islands Private Funds Act (2021 Revision)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            publication_date=datetime(2021, 1, 1),
            section_reference="Part II, Section 8 – Registration of Private Funds",
            reliability_score=0.97,
            raw_excerpt=None,
        ))
        manager.add_citation(CitationRecord(
            source_name="Cayman Islands Monetary Authority",
            source_url="https://www.cima.ky",
            authority=SourceAuthority.PRIMARY,
            publication_date=datetime(2024, 3, 1),
            section_reference="Regulatory Handbook – Chapter 2, Fund Registration",
            reliability_score=0.90,
            raw_excerpt=None,
        ))
        manager.add_citation(CitationRecord(
            source_name="Walkers Global – Cayman Islands Fund Formation Guide",
            source_url="https://www.walkersglobal.com",
            authority=SourceAuthority.SECONDARY,
            publication_date=datetime(2024, 6, 15),
            section_reference="Fund Structures Overview",
            reliability_score=0.80,
            raw_excerpt=None,
        ))

        governance = manager.build()

        entry = RegulatoryEntry(
            jurisdiction_code="KY",
            jurisdiction_name="Cayman Islands",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="Cayman Islands Monetary Authority (CIMA)",
            secondary_regulators=["Cayman Islands Department of International Tax Cooperation"],
            permitted_fund_structures=[
                FundStructure(
                    structure_type="Administered Mutual Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        currency="USD",
                        amount_usd_equivalent=Decimal("0"),
                        notes="No statutory minimum; market practice suggests USD 100,000 minimum seed capital",
                    ),
                    notes="Must have a CIMA-approved administrator; regulated under Mutual Funds Act",
                ),
                FundStructure(
                    structure_type="Managed Mutual Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No statutory minimum; must appoint CIMA-approved manager",
                    ),
                    notes="Regulated under Mutual Funds Act; manager must be licensed",
                ),
                FundStructure(
                    structure_type="Private Fund",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No minimum capital requirement under Private Funds Act",
                    ),
                    notes="Registered under Private Funds Act (2021); 15+ investors exempt from registration",
                ),
                FundStructure(
                    structure_type="Master-Feeder Structure",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("0"),
                        amount_usd_equivalent=None,
                        currency="USD",
                        notes="No separate minimum; component funds meet respective requirements",
                    ),
                    notes="Commonly used for US tax-exempt investors; master fund typically a private fund",
                ),
            ],
            investor_requirements=InvestorRequirements(
                qualified_investor_required=False,
                min_investment_usd=Decimal("0"),
                residency_restrictions=[],
                accreditation_standard="No statutory accreditation standard for mutual funds",
                notes="Private Funds Act restricts to qualified participants (min USD 100,000 investment or net worth > USD 1M)",
            ),
            filing_obligations=[
                RegulatoryFiling(
                    filing_type="Annual Return",
                    frequency="Annual",
                    regulator="CIMA",
                    deadline_description="Within 6 months of fiscal year end",
                    format_required="Electronic via CIMA portal",
                ),
                RegulatoryFiling(
                    filing_type="Audited Financial Statements",
                    frequency="Annual",
                    regulator="CIMA",
                    deadline_description="Within 6 months of fiscal year end",
                    format_required="Audited by CIMA-approved auditor",
                ),
                RegulatoryFiling(
                    filing_type="Fund Annual Report",
                    frequency="Annual",
                    regulator="CIMA",
                    deadline_description="Within 6 months of fiscal year end",
                ),
                RegulatoryFiling(
                    filing_type="Material Change Notification",
                    frequency="Ad-hoc",
                    regulator="CIMA",
                    deadline_description="Promptly upon occurrence",
                ),
            ],
            licensing_requirements=[
                LicensingRequirement(
                    licence_type="Mutual Fund Licence (Administered)",
                    issuing_authority="Cayman Islands Monetary Authority (CIMA)",
                    applies_to="Fund",
                    statutory_reference="Mutual Funds Act (2021 Revision), Part I",
                    notes="Administered funds must appoint a CIMA-approved administrator who holds the licence",
                ),
                LicensingRequirement(
                    licence_type="Mutual Fund Licence (Managed)",
                    issuing_authority="CIMA",
                    applies_to="Fund",
                    statutory_reference="Mutual Funds Act (2021 Revision), Part I",
                    notes="Managed funds must appoint a CIMA-approved manager",
                ),
                LicensingRequirement(
                    licence_type="Private Fund Registration",
                    issuing_authority="CIMA",
                    applies_to="Fund",
                    statutory_reference="Private Funds Act (2021 Revision), Section 8",
                    notes="Simplified registration; no licence required but must register with CIMA",
                ),
            ],
            substance_requirements=SubstanceRequirement(
                local_office_required=True,
                local_directors_required=False,
                minimum_local_directors=None,
                local_staff_required=False,
                minimum_local_staff=None,
                notes="Must maintain a registered office in Cayman Islands; no statutory requirement for local directors or staff",
            ),
            regulatory_timelines=[
                RegulatoryTimeline(
                    process_name="Fund Registration (Administered)",
                    minimum_days=5,
                    maximum_days=15,
                    typical_days=7,
                    notes="Fast-track available; CIMA typically processes within 7 business days for complete applications",
                ),
                RegulatoryTimeline(
                    process_name="Fund Registration (Managed)",
                    minimum_days=5,
                    maximum_days=15,
                    typical_days=7,
                    notes="Same timeline as administered funds",
                ),
                RegulatoryTimeline(
                    process_name="Private Fund Registration",
                    minimum_days=1,
                    maximum_days=5,
                    typical_days=3,
                    notes="Expedited registration; can be completed within 3 business days",
                ),
            ],
            regulatory_costs=[
                RegulatoryCost(
                    cost_type="CIMA Annual Fee – Mutual Fund",
                    amount=Decimal("5000"),
                    currency="USD",
                    amount_usd_equivalent=Decimal("5000"),
                    frequency="Annual",
                    notes="Based on fund size; USD 5,000 for funds under USD 100M NAV",
                ),
                RegulatoryCost(
                    cost_type="CIMA Annual Fee – Private Fund",
                    amount=Decimal("1500"),
                    currency="USD",
                    amount_usd_equivalent=Decimal("1500"),
                    frequency="Annual",
                    notes="Reduced fee for private funds",
                ),
                RegulatoryCost(
                    cost_type="Government Annual Fee",
                    amount=Decimal("500"),
                    currency="USD",
                    amount_usd_equivalent=Decimal("500"),
                    frequency="Annual",
                    notes="Cayman Islands government annual return fee",
                ),
            ],
            penalty_exposure=[
                PenaltyExposure(
                    breach_type="Late Filing of Annual Return",
                    maximum_fine_usd=Decimal("10000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="CIMA may impose fines and ultimately revoke registration for persistent non-compliance",
                ),
                PenaltyExposure(
                    breach_type="AML Breach",
                    maximum_fine_usd=Decimal("500000"),
                    criminal_liability=True,
                    licence_revocation_possible=True,
                    notes="Under Proceeds of Crime Act; criminal penalties for AML/CFT violations",
                ),
                PenaltyExposure(
                    breach_type="Unauthorised Fund Activity",
                    maximum_fine_usd=Decimal("100000"),
                    criminal_liability=True,
                    licence_revocation_possible=True,
                    notes="Operating without CIMA registration is a criminal offence",
                ),
            ],
            wind_down_procedure=WindDownProcedure(
                voluntary_liquidation_available=True,
                typical_duration_days=90,
                regulator_approval_required=True,
                creditor_protection_period_days=30,
                notes="Voluntary liquidation requires CIMA approval and creditor notification; typical completion within 3 months",
            ),
            fund_manager_requirements=FundManagerRequirement(
                local_manager_required=False,
                minimum_aum_for_full_licence_usd=None,
                fit_and_proper_required=True,
                experience_years_required=None,
                notes="No statutory requirement for locally domiciled manager; manager must be approved by CIMA if acting as operator of a managed mutual fund",
            ),
            marketing_restrictions=[
                MarketingRestriction(
                    target_investor_type="Accredited",
                    permitted_jurisdictions=["Global"],
                    restricted_jurisdictions=["US", "CA"],
                    pre_marketing_allowed=True,
                    notes="Regulation S safe harbour for non-US offerings; private placement for US investors under Rule 144A",
                ),
                MarketingRestriction(
                    target_investor_type="Professional",
                    permitted_jurisdictions=["Global"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=True,
                    notes="Professional and sophisticated investors welcome; no EU passport",
                ),
            ],
            beneficial_ownership_rules=BeneficialOwnershipRule(
                register_required=True,
                register_public=False,
                threshold_percentage=Decimal("25"),
                filing_authority="Cayman Islands Department for International Tax Cooperation",
                notes="Beneficial Ownership Register maintained centrally; not publicly accessible; disclosure threshold at 25%",
            ),
            record_retention_policies=[
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="All Fund Records",
                    statutory_reference="Mutual Funds Act (2021 Revision), Section 24",
                    notes="Fund records must be retained for a minimum of 5 years from the date of creation",
                ),
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="AML Records",
                    statutory_reference="Proceeds of Crime Act (2021 Revision), AML Regulations",
                    notes="AML/CFT records must be retained for at least 5 years after business relationship ends",
                ),
            ],
            tax_summary="No corporate income tax, capital gains tax, withholding tax, or VAT. Annual government fee applies.",
            withholding_tax_rate=Decimal("0"),
            aml_kyc_framework="CIMA AML/CFT Guidance Notes (2023); Proceeds of Crime Act (2021 Revision)",
            passporting_available=False,
            passporting_notes="No EU passporting; Cayman Islands is a third-country jurisdiction",
            source_governance=governance,
            confidence=self._placeholder_confidence(),
            version=VersionRecord(
                version_id="1.0.0",
                author="legal-swarm-system",
                change_summary="Initial Cayman Islands regulatory entry",
            ),
        )
        return entry
