from src.agents.base_agent import BaseAgent
from src.schema.schema import RegulatoryEntry


class FundStructureAgent(BaseAgent):
    agent_id = "fund-structure-agent"
    agent_description = "Validates fund structures"

    def process(self, entry: RegulatoryEntry) -> RegulatoryEntry:
        return entry

    def validate(self, entry: RegulatoryEntry) -> bool:
        return len(entry.permitted_fund_structures) > 0
