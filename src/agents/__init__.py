from pathlib import Path

from src.agents.orchestrator import Orchestrator
from src.agents.jurisdiction.regulatory_authority_agent import RegulatoryAuthorityAgent
from src.agents.jurisdiction.licensing_agent import LicensingAgent
from src.agents.jurisdiction.capital_requirement_agent import CapitalRequirementAgent
from src.agents.jurisdiction.fund_structure_agent import FundStructureAgent
from src.agents.jurisdiction.tax_framework_agent import TaxFrameworkAgent
from src.agents.jurisdiction.compliance_obligation_agent import ComplianceObligationAgent


def create_default_orchestrator(audit_log_path: Path | None = None) -> Orchestrator:
    agents = [
        RegulatoryAuthorityAgent(),
        LicensingAgent(),
        CapitalRequirementAgent(),
        FundStructureAgent(),
        TaxFrameworkAgent(),
        ComplianceObligationAgent(),
    ]
    return Orchestrator(agents=agents, audit_log_path=audit_log_path or Path("logs/audit.jsonl"))
