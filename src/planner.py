"""A small planner port. The graph never constructs a provider client."""
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from .contracts import Proposal


class ModelResult:
    def __init__(self, proposal: Proposal | None, reported_tokens: int | None, parsing_failed: bool = False):
        self.proposal = proposal
        self.reported_tokens = reported_tokens
        self.parsing_failed = parsing_failed


class FakePlanner:
    """Repeatable stand-in for a live model. No API key and no network."""

    def __init__(self):
        self.runnable = RunnableLambda(self._respond)

    def _respond(self, item: dict) -> ModelResult:
        scenario, attempt = item["scenario"], item["attempt"]
        invoice = "SAP-9999" if scenario == "wrong_invoice" else "SAP-8841"
        data = {
            "action": "investigate" if scenario == "loop" else "create_review_task",
            "case_id": "SF-1042",
            "invoice_id": invoice,
            "summary": "Review suspected duplicate renewal charge against the linked invoice.",
            "evidence_refs": ["SF-1042", invoice],
        }
        if scenario == "malformed" and attempt == 1:
            data["action"] = "refund_now"
        try:
            return ModelResult(Proposal.model_validate(data), 240)
        except ValidationError:
            return ModelResult(None, 240, parsing_failed=True)

    def propose(self, evidence: dict, attempt: int, scenario: str) -> ModelResult:
        return self.runnable.invoke({"evidence": evidence, "attempt": attempt, "scenario": scenario})
