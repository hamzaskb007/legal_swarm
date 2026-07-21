from dataclasses import dataclass, field
from pathlib import Path

from src.agents.base_agent import BaseAgent
from src.audit.logger import AuditLogger
from src.schema.schema import AuditEventType, RegulatoryEntry


@dataclass
class OrchestrationReport:
    jurisdiction_code: str
    agents_run: list[str] = field(default_factory=list)
    agents_passed: list[str] = field(default_factory=list)
    agents_failed: list[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None


class Orchestrator:
    def __init__(
        self, agents: list[BaseAgent], audit_log_path: Path = Path("logs/audit.jsonl")
    ) -> None:
        self.agents = agents
        self._logger = AuditLogger(log_path=audit_log_path)

    def run(self, entry: RegulatoryEntry) -> tuple[RegulatoryEntry, OrchestrationReport]:
        report = OrchestrationReport(jurisdiction_code=entry.jurisdiction_code)
        for agent in self.agents:
            report.agents_run.append(agent.agent_id)
            entry = agent.process(entry)
            if agent.validate(entry):
                report.agents_passed.append(agent.agent_id)
            else:
                report.agents_failed.append(agent.agent_id)
                report.blocked = True
                report.block_reason = f"Agent {agent.agent_id} validation failed"
                self._logger.log(
                    event_type=AuditEventType.VALIDATION,
                    actor=agent.agent_id,
                    jurisdiction_code=entry.jurisdiction_code,
                    entry_id=entry.entry_id,
                    payload={"blocked": True, "reason": report.block_reason},
                    outcome="BLOCKED",
                )
                break
        if not report.blocked:
            self._logger.log(
                event_type=AuditEventType.VALIDATION,
                actor="orchestrator",
                jurisdiction_code=entry.jurisdiction_code,
                entry_id=entry.entry_id,
                payload={"agents_run": report.agents_run, "all_passed": True},
                outcome="ORCHESTRATION_COMPLETE",
            )
        return entry, report
