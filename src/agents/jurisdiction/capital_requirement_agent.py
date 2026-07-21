from src.agents.base_agent import BaseAgent
from src.schema.schema import RegulatoryEntry


class CapitalRequirementAgent(BaseAgent):
    agent_id = "capital-requirement-agent"
    agent_description = "Validates capital requirements"

    def process(self, entry: RegulatoryEntry) -> RegulatoryEntry:
        return entry

    def validate(self, entry: RegulatoryEntry) -> bool:
        return any(fs.min_capital is not None for fs in entry.permitted_fund_structures)
