from src.agents.base_agent import BaseAgent
from src.schema.schema import RegulatoryEntry


class RegulatoryAuthorityAgent(BaseAgent):
    agent_id = "regulatory-authority-agent"
    agent_description = "Validates regulatory authority information"

    def process(self, entry: RegulatoryEntry) -> RegulatoryEntry:
        return entry

    def validate(self, entry: RegulatoryEntry) -> bool:
        return bool(entry.primary_regulator and entry.primary_regulator.strip()) and isinstance(
            entry.secondary_regulators, list
        )
