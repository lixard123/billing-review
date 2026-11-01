"""Visible workflow. Each node has one job. Decisions live in learner_decisions.py."""
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .contracts import EVIDENCE, State, digest
from .learner_decisions import (
    action_key,
    approval_decision,
    check_access,
    reserve_call,
    validate_proposal,
)


def build_graph(checkpointer, harness):
    def read_case(state: State):
        denied = check_access(harness.principal, state["tenant_id"])
        if denied:
            return denied
        evidence = dict(EVIDENCE)
        evidence["scenario"] = state.get("scenario", "happy")
        return {"status": "ready", "evidence": evidence, "audit": ["read_case"]}

    def reserve(state: State):
        update = reserve_call(state, harness.settings)
        if update.get("status") == "failed":
            return update
        return {**update, "audit": ["reserve"]}

    def propose(state: State):
        result = harness.planner.propose(
            state["evidence"], state.get("model_calls", 0), state.get("scenario", "happy")
        )
        reported = state.get("reported_tokens", 0) + (result.reported_tokens or 0)
        if result.parsing_failed or result.proposal is None:
            return {"status": "planning", "reported_tokens": reported, "proposal": {}, "audit": ["repair"]}
        return {
            "status": "planning",
            "proposal": result.proposal.model_dump(),
            "reported_tokens": reported,
            "audit": ["propose"],
        }

    def validate(state: State):
        problem = validate_proposal(state["evidence"], state["proposal"])
        if problem:
            return problem
        return {
            "status": "review",
            "proposal_hash": digest(state["proposal"]),
            "approval_expires_at": harness.clock() + harness.settings.approval_ttl_seconds,
            "audit": ["review"],
        }

    def approval(state: State):
        answer = interrupt({
            "question": "Approve this billing review task?",
            "proposal_hash": state["proposal_hash"],
            "case_id": state["evidence"]["case_id"],
            "invoice_id": state["evidence"]["invoice_id"],
        })
        decision = approval_decision(
            harness.principal,
            answer if isinstance(answer, dict) else {},
            state["proposal_hash"],
            harness.clock(),
            state["approval_expires_at"],
            state["tenant_id"],
        )
        if decision.get("decision") == "rejected":
            return {"status": "rejected", "audit": ["rejected"]}
        if not decision.get("ok"):
            return decision["failure"]
        return {"status": "approved", "approved_by": decision["approved_by"], "audit": ["approved"]}

    def execute(state: State):
        key = action_key(state["tenant_id"], state["request_id"], state["proposal_hash"])
        payload = {
            "case_id": state["proposal"]["case_id"],
            "invoice_id": state["proposal"]["invoice_id"],
            "summary": state["proposal"]["summary"],
            "proposal_hash": state["proposal_hash"],
        }
        receipt = harness.ledger.create(key, payload)
        return {"status": "completed", "receipt": receipt, "audit": ["completed"]}

    def after_read(state: State):
        return "stop" if state.get("status") == "failed" else "reserve"

    def after_reserve(state: State):
        return "stop" if state.get("status") == "failed" else "propose"

    def after_propose(state: State):
        if (state.get("proposal") or {}).get("action") == "create_review_task":
            return "validate"
        return "reserve"

    def after_validate(state: State):
        return "stop" if state.get("status") == "failed" else "approval"

    def after_approval(state: State):
        return "execute" if state.get("status") == "approved" else "stop"

    builder = StateGraph(State)
    builder.add_node("read_case", read_case)
    builder.add_node("reserve", reserve)
    builder.add_node("propose", propose)
    builder.add_node("validate", validate)
    builder.add_node("approval", approval)
    builder.add_node("execute", execute)
    builder.add_edge(START, "read_case")
    builder.add_conditional_edges("read_case", after_read, {"reserve": "reserve", "stop": END})
    builder.add_conditional_edges("reserve", after_reserve, {"propose": "propose", "stop": END})
    builder.add_conditional_edges("propose", after_propose, {"validate": "validate", "reserve": "reserve"})
    builder.add_conditional_edges("validate", after_validate, {"approval": "approval", "stop": END})
    builder.add_conditional_edges("approval", after_approval, {"execute": "execute", "stop": END})
    builder.add_edge("execute", END)
    return builder.compile(checkpointer=checkpointer)
