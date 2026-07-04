from src.agents.base_agent import BaseAgent
from src.schema.schema import RegulatoryEntry


class LicensingAgent(BaseAgent):
    agent_id = "licensing-agent"
    agent_description = "Validates licensing requirements"

    def process(self, entry: RegulatoryEntry) -> RegulatoryEntry:
        return entry

    def validate(self, entry: RegulatoryEntry) -> bool:
        return entry.licensing_requirements is not None and len(entry.licensing_requirements) > 0
