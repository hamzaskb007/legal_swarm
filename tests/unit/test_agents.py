"""Unit tests for agent architecture."""

import pytest
from decimal import Decimal
from pathlib import Path

from src.agents.base_agent import BaseAgent
from src.agents.jurisdiction.regulatory_authority_agent import RegulatoryAuthorityAgent
from src.agents.jurisdiction.licensing_agent import LicensingAgent
from src.agents.jurisdiction.capital_requirement_agent import CapitalRequirementAgent
from src.agents.jurisdiction.fund_structure_agent import FundStructureAgent
from src.agents.jurisdiction.tax_framework_agent import TaxFrameworkAgent
from src.agents.jurisdiction.compliance_obligation_agent import ComplianceObligationAgent
from src.agents.orchestrator import Orchestrator, OrchestrationReport
from src.agents import create_default_orchestrator
from src.schema.schema import (
    CapitalRequirement,
    FundStructure,
    LicensingRequirement,
    RegulatoryEntry,
    RegulatoryFiling,
)
from tests.unit.test_schema import make_entry


class TestRegulatoryAuthorityAgent:
    def test_agent_id(self) -> None:
        agent = RegulatoryAuthorityAgent()
        assert agent.agent_id == "regulatory-authority-agent"

    def test_validate_passes(self) -> None:
        agent = RegulatoryAuthorityAgent()
        entry = make_entry(primary_regulator="SCA", secondary_regulators=["DFSA"])
        assert agent.validate(entry) is True

    def test_validate_fails_empty_regulator(self) -> None:
        agent = RegulatoryAuthorityAgent()
        entry = make_entry(primary_regulator="", secondary_regulators=[])
        assert agent.validate(entry) is False

    def test_process_returns_entry_unchanged(self) -> None:
        agent = RegulatoryAuthorityAgent()
        entry = make_entry()
        result = agent.process(entry)
        assert result is entry


class TestLicensingAgent:
    def test_validate_passes_with_licensing(self) -> None:
        agent = LicensingAgent()
        entry = make_entry(
            licensing_requirements=[
                LicensingRequirement(
                    licence_type="Test", issuing_authority="SCA", applies_to="Fund"
                )
            ]
        )
        assert agent.validate(entry) is True

    def test_validate_fails_when_none(self) -> None:
        agent = LicensingAgent()
        entry = make_entry(licensing_requirements=None)
        assert agent.validate(entry) is False

    def test_validate_fails_when_empty(self) -> None:
        agent = LicensingAgent()
        entry = make_entry(licensing_requirements=[])
        assert agent.validate(entry) is False


class TestCapitalRequirementAgent:
    def _fund_structure(self, **kwargs: object) -> FundStructure:
        defaults: dict[str, object] = dict(
            structure_type="Test", is_permitted=True, max_leverage_ratio=None
        )
        defaults.update(kwargs)
        return FundStructure(**defaults)  # type: ignore[arg-type]

    def test_validate_passes_with_capital(self) -> None:
        agent = CapitalRequirementAgent()
        entry = make_entry(
            permitted_fund_structures=[
                self._fund_structure(
                    min_capital=CapitalRequirement(
                        amount=None, currency="USD", amount_usd_equivalent=None, notes=None
                    ),
                )
            ]
        )
        assert agent.validate(entry) is True

    def test_validate_fails_no_capital(self) -> None:
        agent = CapitalRequirementAgent()
        entry = make_entry(permitted_fund_structures=[self._fund_structure()])
        assert agent.validate(entry) is False

    def test_validate_fails_empty(self) -> None:
        agent = CapitalRequirementAgent()
        entry = make_entry(permitted_fund_structures=[])
        assert agent.validate(entry) is False


class TestFundStructureAgent:
    def _fund_structure(self, **kwargs: object) -> FundStructure:
        defaults: dict[str, object] = dict(
            structure_type="Test", is_permitted=True, max_leverage_ratio=None
        )
        defaults.update(kwargs)
        return FundStructure(**defaults)  # type: ignore[arg-type]

    def test_validate_passes(self) -> None:
        agent = FundStructureAgent()
        entry = make_entry(permitted_fund_structures=[self._fund_structure()])
        assert agent.validate(entry) is True

    def test_validate_fails_empty(self) -> None:
        agent = FundStructureAgent()
        entry = make_entry(permitted_fund_structures=[])
        assert agent.validate(entry) is False


class TestTaxFrameworkAgent:
    def test_validate_passes(self) -> None:
        entry = make_entry(tax_summary="No tax", withholding_tax_rate=Decimal("0"))
        assert TaxFrameworkAgent().validate(entry) is True

    def test_validate_fails_no_tax_summary(self) -> None:
        entry = make_entry(tax_summary=None, withholding_tax_rate=Decimal("0"))
        assert TaxFrameworkAgent().validate(entry) is False

    def test_validate_fails_no_withholding(self) -> None:
        entry = make_entry(tax_summary="No tax", withholding_tax_rate=None)
        assert TaxFrameworkAgent().validate(entry) is False


class TestComplianceObligationAgent:
    def _entry(self, **kwargs: object) -> RegulatoryEntry:
        defaults: dict[str, object] = dict(
            filing_obligations=[
                RegulatoryFiling(filing_type="AR", frequency="Annual", regulator="SCA")
            ],
            aml_kyc_framework="AML Law",
        )
        defaults.update(kwargs)
        return make_entry(**defaults)

    def test_validate_passes(self) -> None:
        assert ComplianceObligationAgent().validate(self._entry()) is True

    def test_validate_fails_no_filings(self) -> None:
        assert ComplianceObligationAgent().validate(self._entry(filing_obligations=[])) is False

    def test_validate_fails_no_aml(self) -> None:
        assert ComplianceObligationAgent().validate(self._entry(aml_kyc_framework=None)) is False


class TestBaseAgent:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseAgent()  # type: ignore[abstract]


class TestOrchestrator:
    @pytest.fixture
    def entry(self) -> RegulatoryEntry:
        return make_entry(
            primary_regulator="SCA",
            secondary_regulators=["DFSA"],
            licensing_requirements=[
                LicensingRequirement(
                    licence_type="Test", issuing_authority="SCA", applies_to="Fund"
                )
            ],
            permitted_fund_structures=[
                FundStructure(
                    structure_type="Test",
                    is_permitted=True,
                    max_leverage_ratio=None,
                    min_capital=CapitalRequirement(
                        amount=Decimal("1000"),
                        currency="USD",
                        amount_usd_equivalent=None,
                        notes=None,
                    ),
                )
            ],
            tax_summary="No tax",
            withholding_tax_rate=Decimal("0"),
            filing_obligations=[
                RegulatoryFiling(filing_type="AR", frequency="Annual", regulator="SCA")
            ],
            aml_kyc_framework="AML Law",
        )

    @pytest.fixture
    def all_agents(self) -> list[BaseAgent]:
        return [
            RegulatoryAuthorityAgent(),
            LicensingAgent(),
            CapitalRequirementAgent(),
            FundStructureAgent(),
            TaxFrameworkAgent(),
            ComplianceObligationAgent(),
        ]

    def test_orchestrator_run_all_pass(
        self, entry: RegulatoryEntry, all_agents: list[BaseAgent], tmp_path: Path
    ) -> None:
        orchestrator = Orchestrator(agents=all_agents, audit_log_path=tmp_path / "audit.jsonl")
        _result_entry, report = orchestrator.run(entry)
        assert report.blocked is False
        assert len(report.agents_run) == 6
        assert len(report.agents_passed) == 6
        assert len(report.agents_failed) == 0

    def test_orchestrator_blocked_on_failure(
        self, all_agents: list[BaseAgent], tmp_path: Path
    ) -> None:
        entry = make_entry(primary_regulator="")
        orchestrator = Orchestrator(agents=all_agents, audit_log_path=tmp_path / "audit.jsonl")
        _result_entry, report = orchestrator.run(entry)
        assert report.blocked is True
        assert len(report.agents_failed) == 1
        assert report.block_reason is not None

    def test_orchestrator_audit_log_on_blocked(
        self, all_agents: list[BaseAgent], tmp_path: Path
    ) -> None:
        entry = make_entry(primary_regulator="")
        log_path = tmp_path / "audit.jsonl"
        orchestrator = Orchestrator(agents=all_agents, audit_log_path=log_path)
        orchestrator.run(entry)
        logs = log_path.read_text()
        assert "BLOCKED" in logs

    def test_orchestrator_audit_log_on_success(
        self, entry: RegulatoryEntry, all_agents: list[BaseAgent], tmp_path: Path
    ) -> None:
        log_path = tmp_path / "audit.jsonl"
        orchestrator = Orchestrator(agents=all_agents, audit_log_path=log_path)
        orchestrator.run(entry)
        logs = log_path.read_text()
        assert "ORCHESTRATION_COMPLETE" in logs

    def test_create_default_orchestrator(self, tmp_path: Path) -> None:
        orchestrator = create_default_orchestrator(audit_log_path=tmp_path / "audit.jsonl")
        assert len(orchestrator.agents) == 6
        assert orchestrator.agents[0].agent_id == "regulatory-authority-agent"

    def test_orchestration_report_dataclass(self) -> None:
        report = OrchestrationReport(jurisdiction_code="AE")
        assert report.jurisdiction_code == "AE"
        assert report.agents_run == []
        assert report.blocked is False
