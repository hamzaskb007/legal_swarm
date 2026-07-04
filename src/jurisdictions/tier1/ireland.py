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


class IrelandBuilder(JurisdictionBuilder):
    """Builder for Ireland (IE) – leading UCITS and AIFMD hub."""

    def build_entry(self) -> RegulatoryEntry:
        manager = SourceGovernanceManager()

        manager.add_citation(CitationRecord(
            source_name="European Communities (Undertakings for Collective Investment in Transferable Securities) Regulations 2011 (S.I. No. 352/2011)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2011, 7, 1),
            section_reference="UCITS Regulations 2015 (S.I. No. 439/2015) – Authorisation Requirements",
            reliability_score=0.97,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="European Union (Alternative Investment Fund Managers) Regulations 2013 (S.I. No. 257/2013)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2013, 7, 22),
            section_reference="AIFMD Regulations 2013 – Fund Manager Authorisation",
            reliability_score=0.97,
            raw_excerpt=None,
            regulatory_relevance_tag="Licensing",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Irish Collective Asset-management Vehicles Act 2015",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2015, 12, 14),
            section_reference="Parts 2–4 – ICAV Constitution and Operation",
            reliability_score=0.96,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Structure",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Central Bank of Ireland",
            source_url="https://www.centralbank.ie",
            authority=SourceAuthority.PRIMARY,
            authority_level=1,
            publication_date=datetime(2024, 1, 1),
            section_reference="Fund Authorisation and Supervision – UCITS and AIF frameworks",
            reliability_score=0.90,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))

        governance = manager.build()

        entry = RegulatoryEntry(
            jurisdiction_code="IE",
            jurisdiction_name="Ireland",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="Central Bank of Ireland",
            secondary_regulators=["Department of Finance", "Revenue Commissioners"],
            permitted_fund_structures=[
                FundStructure(
                    structure_type="UCITS",
                    is_permitted=True,
                    min_capital=CapitalRequirement(
                        amount=Decimal("300000"),
                        currency="EUR",
                        amount_usd_equivalent=Decimal("324000"),
                        notes="EUR 300,000 minimum initial capital; must be reached within 6 months",
                    ),
                    max_leverage_ratio=2.0,
                    notes="EU passportable; regulated under UCITS Regulations 2015; available as ICAV or PLC",
                ),
                FundStructure(
                    structure_type="Qualifying Investor AIF (QIAIF)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("125000"),
                        currency="EUR",
                        amount_usd_equivalent=Decimal("135000"),
                        notes="EUR 125,000 minimum investment per investor",
                    ),
                    notes="No Central Bank authorisation delays; for professional and qualifying investors; min EUR 100K investment",
                ),
                FundStructure(
                    structure_type="Retail Investor AIF (RIAIF)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("300000"),
                        currency="EUR",
                        amount_usd_equivalent=Decimal("324000"),
                        notes="EUR 300,000 minimum capital",
                    ),
                    notes="Available to retail investors; full Central Bank authorisation required",
                ),
                FundStructure(
                    structure_type="ICAV (Irish Collective Asset-management Vehicle)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("300000"),
                        currency="EUR",
                        amount_usd_equivalent=Decimal("324000"),
                        notes="Same minimum as underlying fund type",
                    ),
                    notes="Corporate structure for collective investment; tax transparent; governed by ICAV Act 2015",
                ),
            ],
            investor_requirements=InvestorRequirements(
                qualified_investor_required=False,
                min_investment_usd=None,
                residency_restrictions=[],
                accreditation_standard="QIAIF requires 'qualifying investor' (min EUR 100K investment and certification)",
                notes="UCITS and RIAIF available to retail; QIAIF restricted to professional/qualifying investors",
            ),
            filing_obligations=[
                RegulatoryFiling(
                    filing_type="Annual Report",
                    frequency="Annual",
                    regulator="Central Bank of Ireland",
                    deadline_description="Within 4 months of fiscal year end for UCITS; 6 months for AIFs",
                    format_required="XBRL via ONR system",
                ),
                RegulatoryFiling(
                    filing_type="Semi-Annual Report",
                    frequency="Semi-Annual",
                    regulator="Central Bank of Ireland",
                    deadline_description="Within 2 months of period end",
                ),
                RegulatoryFiling(
                    filing_type="AIFMD Annex IV Reporting",
                    frequency="Quarterly",
                    regulator="Central Bank of Ireland",
                    deadline_description="Within 45 days of quarter end",
                    format_required="XML",
                ),
                RegulatoryFiling(
                    filing_type="UCITS KIID/PRIIPs KID",
                    frequency="Upon update",
                    regulator="Central Bank of Ireland",
                    deadline_description="Ongoing; must be reviewed annually",
                    format_required="Prescribed template",
                ),
            ],
            licensing_requirements=[
                LicensingRequirement(
                    licence_type="Central Bank Authorisation – UCITS",
                    issuing_authority="Central Bank of Ireland",
                    applies_to="Fund",
                    statutory_reference="UCITS Regulations 2015 (S.I. No. 439/2015)",
                    notes="Full Central Bank authorisation required for UCITS funds",
                ),
                LicensingRequirement(
                    licence_type="Central Bank Authorisation – AIF",
                    issuing_authority="Central Bank of Ireland",
                    applies_to="Fund",
                    statutory_reference="AIFMD Regulations 2013 (S.I. No. 257/2013)",
                    notes="AIF authorisation for RIAIF and QIAIF funds",
                ),
                LicensingRequirement(
                    licence_type="AIFM Licence",
                    issuing_authority="Central Bank of Ireland",
                    applies_to="Manager",
                    statutory_reference="AIFMD Regulations 2013 (S.I. No. 257/2013), Part 2",
                    notes="Required for AIFMs managing funds above thresholds; regulated by Central Bank",
                ),
            ],
            substance_requirements=SubstanceRequirement(
                local_office_required=True,
                local_directors_required=True,
                minimum_local_directors=2,
                local_staff_required=False,
                minimum_local_staff=None,
                notes="Funds must have registered office in Ireland; at least 2 Irish-resident directors required for ICAV; Central Bank requires sufficient substance",
            ),
            regulatory_timelines=[
                RegulatoryTimeline(
                    process_name="UCITS Authorisation",
                    minimum_days=60,
                    maximum_days=180,
                    typical_days=120,
                    notes="Central Bank review takes 2–6 months; pre-submission engagement recommended",
                ),
                RegulatoryTimeline(
                    process_name="QIAIF Authorisation",
                    minimum_days=15,
                    maximum_days=30,
                    typical_days=20,
                    notes="QIAIF benefits from streamlined 'fast-track' 24-hour review for certain structures; full approval typically within 20 business days",
                ),
                RegulatoryTimeline(
                    process_name="RIAIF Authorisation",
                    minimum_days=60,
                    maximum_days=120,
                    typical_days=90,
                    notes="Full Central Bank review for retail AIFs; typically 3–4 months",
                ),
            ],
            regulatory_costs=[
                RegulatoryCost(
                    cost_type="Central Bank Authorisation Fee – UCITS",
                    amount=Decimal("12000"),
                    currency="EUR",
                    amount_usd_equivalent=Decimal("13000"),
                    frequency="One-time",
                    notes="One-time application fee for UCITS funds",
                ),
                RegulatoryCost(
                    cost_type="Central Bank Annual Supervision Fee",
                    amount=Decimal("6000"),
                    currency="EUR",
                    amount_usd_equivalent=Decimal("6500"),
                    frequency="Annual",
                    notes="Annual fee based on fund NAV and complexity",
                ),
                RegulatoryCost(
                    cost_type="ICAV Incorporation Fee",
                    amount=Decimal("3500"),
                    currency="EUR",
                    amount_usd_equivalent=Decimal("3800"),
                    frequency="One-time",
                    notes="CRO incorporation fee for ICAV structure",
                ),
            ],
            penalty_exposure=[
                PenaltyExposure(
                    breach_type="Late Filing of Annual Return",
                    maximum_fine_usd=Decimal("500000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="Central Bank may impose significant fines for non-compliance with filing obligations",
                ),
                PenaltyExposure(
                    breach_type="AML/CFT Breach",
                    maximum_fine_usd=Decimal("1000000"),
                    criminal_liability=True,
                    licence_revocation_possible=True,
                    notes="Criminal Liability under Criminal Justice Acts; CBI enforcement powers",
                ),
                PenaltyExposure(
                    breach_type="Investment Restriction Breach",
                    maximum_fine_usd=Decimal("250000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="Central Bank enforcement for UCITS/AIF investment limit breaches",
                ),
            ],
            wind_down_procedure=WindDownProcedure(
                voluntary_liquidation_available=True,
                typical_duration_days=120,
                regulator_approval_required=True,
                creditor_protection_period_days=60,
                notes="Voluntary liquidation requires Central Bank approval and High Court supervision for ICAVs; typical duration 3–6 months",
            ),
            fund_manager_requirements=FundManagerRequirement(
                local_manager_required=False,
                minimum_aum_for_full_licence_usd=Decimal("100000000"),
                fit_and_proper_required=True,
                experience_years_required=5,
                notes="AIFM required for funds above EUR 100M (EUR 500M for unleveraged); full fit and proper assessment by Central Bank; minimum 5 years relevant experience for key personnel",
            ),
            marketing_restrictions=[
                MarketingRestriction(
                    target_investor_type="Retail",
                    permitted_jurisdictions=["EU", "EEA"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=True,
                    notes="UCITS eligible for EU passport; KIID/PRIIPs KID required for retail marketing",
                ),
                MarketingRestriction(
                    target_investor_type="Professional",
                    permitted_jurisdictions=["EU", "EEA", "Global"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=True,
                    notes="AIFMD passport for professional investors; QIAIF restricted to qualifying investors only",
                ),
            ],
            beneficial_ownership_rules=BeneficialOwnershipRule(
                register_required=True,
                register_public=True,
                threshold_percentage=Decimal("25"),
                filing_authority="Companies Registration Office (CRO) – Central Register of Beneficial Ownership",
                notes="Central Register of Beneficial Ownership of Companies and Industrial and Provident Societies (RBO); publicly accessible; threshold at 25%",
            ),
            record_retention_policies=[
                RecordRetentionPolicy(
                    minimum_retention_years=6,
                    applies_to="All Fund Records",
                    statutory_reference="Central Bank of Ireland – Fund Management Company Guidance",
                    notes="Fund records must be retained for at least 6 years",
                ),
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="AML Records",
                    statutory_reference="Criminal Justice (Money Laundering and Terrorist Financing) Act 2010",
                    notes="AML records must be retained for at least 5 years after business relationship ends",
                ),
            ],
            tax_summary="No fund-level tax for qualifying investment funds. 25% exit tax for Irish resident investors. VAT exemption for fund management services. Stamp duty exemption for fund assets.",
            withholding_tax_rate=Decimal("0"),
            aml_kyc_framework="Criminal Justice (Money Laundering and Terrorist Financing) Acts 2010–2021; Central Bank AML/CFT guidelines",
            passporting_available=True,
            passporting_notes="Full EU passport for UCITS and AIFMD-compliant AIFs; EEA marketing rights",
            source_governance=governance,
            confidence=self._placeholder_confidence(),
            version=VersionRecord(
                version_id="1.0.0",
                author="legal-swarm-system",
                change_summary="Initial Ireland regulatory entry",
            ),
        )
        return entry
