from src.agents.base_agent import BaseAgent
from src.schema.schema import RegulatoryEntry


class ComplianceObligationAgent(BaseAgent):
    agent_id = "compliance-obligation-agent"
    agent_description = "Validates compliance obligations"

    def process(self, entry: RegulatoryEntry) -> RegulatoryEntry:
        return entry

    def validate(self, entry: RegulatoryEntry) -> bool:
        return len(entry.filing_obligations) > 0 and entry.aml_kyc_framework is not None
