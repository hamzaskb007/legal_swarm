from abc import ABC, abstractmethod
from src.schema.schema import RegulatoryEntry


class BaseAgent(ABC):
    agent_id: str = "base"
    agent_description: str = "Base agent"

    @abstractmethod
    def process(self, entry: RegulatoryEntry) -> RegulatoryEntry:
        """Process and validate a specific aspect of the entry."""
        ...

    @abstractmethod
    def validate(self, entry: RegulatoryEntry) -> bool:
        """Return True if this agent's domain is complete and valid."""
        ...
