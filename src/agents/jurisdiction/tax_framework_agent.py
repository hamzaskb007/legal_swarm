from src.agents.base_agent import BaseAgent
from src.schema.schema import RegulatoryEntry


class TaxFrameworkAgent(BaseAgent):
    agent_id = "tax-framework-agent"
    agent_description = "Validates tax framework information"

    def process(self, entry: RegulatoryEntry) -> RegulatoryEntry:
        return entry

    def validate(self, entry: RegulatoryEntry) -> bool:
        return entry.tax_summary is not None and entry.withholding_tax_rate is not None
