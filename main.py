"""Run one synthetic billing review. No API key is required."""
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from src.contracts import DIRECTORY, Settings
from src.graph import build_graph
from src.learner_decisions import TaskLedger
from src.planner import FakePlanner


class Harness:
    def __init__(self):
        self.settings = Settings()
        self.planner = FakePlanner()
        self.ledger = TaskLedger()
        self.principal = DIRECTORY["analyst"]
        self.clock = lambda: 1000


def main() -> None:
    harness = Harness()
    graph = build_graph(InMemorySaver(), harness)
    config = {"configurable": {"thread_id": "demo-sf-1042"}, "recursion_limit": 40}
    first = graph.invoke(
        {
            "request_id": "request-1",
            "tenant_id": "acme-in",
            "case_id": "SF-1042",
            "scenario": "happy",
            "status": "new",
            "model_calls": 0,
            "reserved_tokens": 0,
            "reported_tokens": 0,
            "audit": [],
        },
        config,
    )
    print("=== BILLING REVIEW REPORT ===")
    print("Case: SF-1042")
    print("Invoice: SAP-8841")
    print("Status before approval: review")
    print(f"Tasks before approval: {len(harness.ledger.all())}")
    print(f"Model calls: {first['model_calls']}")
    harness.principal = DIRECTORY["manager"]
    final = graph.invoke(
        Command(resume={"approved": True, "proposal_hash": first["proposal_hash"]}),
        config,
    )
    print(f"Status after approval: {final['status']}")
    print(f"Approved by: {final['approved_by']}")
    print(f"Tasks after approval: {len(harness.ledger.all())}")


if __name__ == "__main__":
    main()
