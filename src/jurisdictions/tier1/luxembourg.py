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


class LuxembourgBuilder(JurisdictionBuilder):
    """Builder for Luxembourg (LU) – the largest UCITS domicile in Europe."""

    def build_entry(self) -> RegulatoryEntry:
        manager = SourceGovernanceManager()

        manager.add_citation(CitationRecord(
            source_name="Luxembourg Law of 17 December 2010 on Undertakings for Collective Investment (UCITS)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2010, 12, 17),
            section_reference="Articles 1–58",
            reliability_score=0.97,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Structure",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Luxembourg Law of 23 July 2016 on Reserved Alternative Investment Funds (RAIF)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2016, 7, 23),
            section_reference="Articles 1–35",
            reliability_score=0.97,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Structure",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Luxembourg Law of 13 February 2007 on Specialised Investment Funds (SIF)",
            source_url=None,
            authority=SourceAuthority.PRIMARY,
            authority_level=2,
            publication_date=datetime(2007, 2, 13),
            section_reference="Chapters 1–4",
            reliability_score=0.96,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Structure",
            last_verified_timestamp=datetime.utcnow(),
        ))
        manager.add_citation(CitationRecord(
            source_name="Commission de Surveillance du Secteur Financier (CSSF)",
            source_url="https://www.cssf.lu",
            authority=SourceAuthority.PRIMARY,
            authority_level=1,
            publication_date=datetime(2024, 4, 1),
            section_reference="Fund Supervision – UCITS, SIF, RAIF frameworks",
            reliability_score=0.90,
            raw_excerpt=None,
            regulatory_relevance_tag="Fund Registration",
            last_verified_timestamp=datetime.utcnow(),
        ))

        governance = manager.build()

        entry = RegulatoryEntry(
            jurisdiction_code="LU",
            jurisdiction_name="Luxembourg",
            tier=JurisdictionTier.TIER_1,
            primary_regulator="Commission de Surveillance du Secteur Financier (CSSF)",
            secondary_regulators=["Banque Centrale du Luxembourg", "Administration de l'Enregistrement"],
            permitted_fund_structures=[
                FundStructure(
                    structure_type="UCITS Part I",
                    is_permitted=True,
                    min_capital=CapitalRequirement(
                        amount=Decimal("1250000"),
                        currency="EUR",
                        amount_usd_equivalent=Decimal("1350000"),
                        notes="EUR 1,250,000 minimum; must be reached within 12 months of authorisation",
                    ),
                    max_leverage_ratio=2.0,
                    notes="UCITS compliant; eligible for EU passporting; regulated under Part I of 2010 Law",
                ),
                FundStructure(
                    structure_type="Part II UCI",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("1250000"),
                        currency="EUR",
                        amount_usd_equivalent=Decimal("1350000"),
                        notes="Same minimum as UCITS; no EU passport",
                    ),
                    notes="Non-UCITS retail fund; regulated under Part II of 2010 Law",
                ),
                FundStructure(
                    structure_type="Specialised Investment Fund (SIF)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("4000000"),
                        currency="EUR",
                        amount_usd_equivalent=Decimal("4320000"),
                        notes="EUR 4M minimum; must be reached within 12 months",
                    ),
                    notes="Well-regulated; suitable for institutional investors; regulated by 2007 SIF Law",
                ),
                FundStructure(
                    structure_type="Reserved Alternative Investment Fund (RAIF)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("4000000"),
                        currency="EUR",
                        amount_usd_equivalent=Decimal("4320000"),
                        notes="EUR 4M minimum; no CSSF authorisation required",
                    ),
                    notes="No direct CSSF supervision; must appoint authorised AIFM; regulated by 2016 RAIF Law",
                ),
                FundStructure(
                    structure_type="SICAR (Investment Company in Risk Capital)",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("1000000"),
                        currency="EUR",
                        amount_usd_equivalent=Decimal("1080000"),
                        notes="EUR 1M minimum",
                    ),
                    notes="Designed for private equity and venture capital; tax transparent",
                ),
            ],
            investor_requirements=InvestorRequirements(
                qualified_investor_required=False,
                min_investment_usd=None,
                residency_restrictions=[],
                accreditation_standard="SIF and RAIF require 'well-informed investor' status (EUR 125K minimum or institutional)",
                notes="UCITS and Part II UCI available to retail investors",
            ),
            filing_obligations=[
                RegulatoryFiling(
                    filing_type="Annual Report",
                    frequency="Annual",
                    regulator="CSSF",
                    deadline_description="Within 6 months of fiscal year end",
                    format_required="CSSF approved format",
                ),
                RegulatoryFiling(
                    filing_type="Semi-Annual Report",
                    frequency="Semi-Annual",
                    regulator="CSSF",
                    deadline_description="Within 2 months of period end",
                ),
                RegulatoryFiling(
                    filing_type="AIFMD Reporting (AIFs only)",
                    frequency="Quarterly",
                    regulator="CSSF",
                    deadline_description="Within 30 days of quarter end",
                    format_required="XML via CSSF e-file",
                ),
                RegulatoryFiling(
                    filing_type="Material Change Notification",
                    frequency="Ad-hoc",
                    regulator="CSSF",
                    deadline_description="Immediately upon occurrence",
                ),
            ],
            licensing_requirements=[
                LicensingRequirement(
                    licence_type="CSSF Authorisation – UCITS",
                    issuing_authority="Commission de Surveillance du Secteur Financier (CSSF)",
                    applies_to="Fund",
                    statutory_reference="Law of 17 December 2010, Part I",
                    notes="Full CSSF authorisation required for UCITS Part I funds",
                ),
                LicensingRequirement(
                    licence_type="AIFM Licence",
                    issuing_authority="CSSF",
                    applies_to="Manager",
                    statutory_reference="Law of 12 July 2013 (AIFM Law)",
                    notes="Required for AIFMs managing RAIF, SIF, SICAR; AIFMD-compliant",
                ),
                LicensingRequirement(
                    licence_type="CSSF Authorisation – SIF / RAIF",
                    issuing_authority="CSSF",
                    applies_to="Fund",
                    statutory_reference="Law of 13 February 2007 (SIF) / Law of 23 July 2016 (RAIF)",
                    notes="SIF requires CSSF authorisation; RAIF does not require CSSF authorisation but must appoint authorised AIFM",
                ),
            ],
            substance_requirements=SubstanceRequirement(
                local_office_required=True,
                local_directors_required=True,
                minimum_local_directors=2,
                local_staff_required=False,
                minimum_local_staff=None,
                notes="Must have registered office in Luxembourg; at least 2 local directors required for most fund structures; substance requirements per CSSF circulars",
            ),
            regulatory_timelines=[
                RegulatoryTimeline(
                    process_name="UCITS Authorisation",
                    minimum_days=90,
                    maximum_days=180,
                    typical_days=120,
                    notes="CSSF review takes 3–6 months for complete applications; pre-submission meetings recommended",
                ),
                RegulatoryTimeline(
                    process_name="SIF Authorisation",
                    minimum_days=60,
                    maximum_days=120,
                    typical_days=90,
                    notes="Expedited compared to UCITS; typically 2–4 months",
                ),
                RegulatoryTimeline(
                    process_name="RAIF Setup",
                    minimum_days=10,
                    maximum_days=30,
                    typical_days=20,
                    notes="No CSSF pre-approval; fund can launch once AIFM is in place",
                ),
            ],
            regulatory_costs=[
                RegulatoryCost(
                    cost_type="CSSF Authorisation Fee – UCITS",
                    amount=Decimal("25000"),
                    currency="EUR",
                    amount_usd_equivalent=Decimal("27000"),
                    frequency="One-time",
                    notes="One-time application fee for UCITS; varies by fund complexity",
                ),
                RegulatoryCost(
                    cost_type="CSSF Annual Supervision Fee",
                    amount=Decimal("5000"),
                    currency="EUR",
                    amount_usd_equivalent=Decimal("5400"),
                    frequency="Annual",
                    notes="Annual CSSF supervision fee based on fund NAV",
                ),
                RegulatoryCost(
                    cost_type="Subscription Tax (Taxe d'abonnement)",
                    amount=Decimal("0"),
                    currency="EUR",
                    amount_usd_equivalent=Decimal("0"),
                    frequency="Annual",
                    notes="0.05% of NAV per annum (reduced to 0.01% for money market and institutional funds); not a fixed fee",
                ),
            ],
            penalty_exposure=[
                PenaltyExposure(
                    breach_type="Late Filing of Annual Report",
                    maximum_fine_usd=Decimal("250000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="CSSF may impose administrative fines and ultimately withdraw authorisation",
                ),
                PenaltyExposure(
                    breach_type="AML/CFT Breach",
                    maximum_fine_usd=Decimal("1000000"),
                    criminal_liability=True,
                    licence_revocation_possible=True,
                    notes="Criminal and administrative sanctions under Luxembourg AML Law",
                ),
                PenaltyExposure(
                    breach_type="Breach of Investment Rules",
                    maximum_fine_usd=Decimal("500000"),
                    criminal_liability=False,
                    licence_revocation_possible=True,
                    notes="CSSF enforcement for UCITS/AIF investment limit violations",
                ),
            ],
            wind_down_procedure=WindDownProcedure(
                voluntary_liquidation_available=True,
                typical_duration_days=180,
                regulator_approval_required=True,
                creditor_protection_period_days=60,
                notes="Voluntary liquidation requires CSSF approval and court-appointed liquidator; typical duration 6–12 months",
            ),
            fund_manager_requirements=FundManagerRequirement(
                local_manager_required=False,
                minimum_aum_for_full_licence_usd=Decimal("100000000"),
                fit_and_proper_required=True,
                experience_years_required=5,
                notes="AIFM licence required for managers above EUR 100M AUM (EUR 500M for unleveraged funds); fit and proper test mandatory; minimum 5 years relevant experience",
            ),
            marketing_restrictions=[
                MarketingRestriction(
                    target_investor_type="Retail",
                    permitted_jurisdictions=["EU", "EEA"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=False,
                    notes="UCITS eligible for passporting across EU/EEA; KIID required for retail marketing",
                ),
                MarketingRestriction(
                    target_investor_type="Professional",
                    permitted_jurisdictions=["EU", "EEA", "Global"],
                    restricted_jurisdictions=[],
                    pre_marketing_allowed=True,
                    notes="AIFMD passport for professional investors across EU/EEA; national private placement regimes for third countries",
                ),
            ],
            beneficial_ownership_rules=BeneficialOwnershipRule(
                register_required=True,
                register_public=True,
                threshold_percentage=Decimal("25"),
                filing_authority="Registre des Bénéficiaires Effectifs (RBE) – Luxembourg Business Registers",
                notes="Beneficial ownership register (RBE) is publicly accessible; threshold at 25% ownership; under Luxembourg Law of 13 January 2019",
            ),
            record_retention_policies=[
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="All Fund Records",
                    statutory_reference="CSSF Circular 18/698",
                    notes="Fund documents must be retained for at least 5 years",
                ),
                RecordRetentionPolicy(
                    minimum_retention_years=5,
                    applies_to="AML Records",
                    statutory_reference="Luxembourg AML Law of 12 November 2004",
                    notes="AML records must be retained for at least 5 years after business relationship ends",
                ),
            ],
            tax_summary="Subscription tax (taxe d'abonnement) of 0.05% p.a. on NAV for UCITS/SIF/RAIF (reduced to 0.01% for money market and institutional funds). No corporate income tax at fund level. VAT exemption for management services.",
            withholding_tax_rate=Decimal("0"),
            aml_kyc_framework="Luxembourg Law of 12 November 2004 on AML/CFT (as amended); CSSF Regulation 12-02",
            passporting_available=True,
            passporting_notes="Full EU passport for UCITS and AIFMD-compliant AIFs; cross-border marketing within EEA",
            source_governance=governance,
            confidence=self._placeholder_confidence(),
            version=VersionRecord(
                version_id="1.0.0",
                author="legal-swarm-system",
                change_summary="Initial Luxembourg regulatory entry",
            ),
        )
        return entry
