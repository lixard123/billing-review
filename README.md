# OCT2 — Billing Review Harness

You are given the workflow. You fill in the decisions the class made visible: who may read a case, when a model call is admitted, whether a proposal matches the invoice, who may approve that exact proposal, and how one approved action keeps a single identity.

The business case is the same one from the session. Salesforce case **SF-1042** says the customer was charged twice. SAP invoice **SAP-8841** is the accounting record. The workflow may propose a ServiceNow review task. It does not issue a refund.

No API key is required. The planner is a local fake.

## What you change

Edit only `src/learner_decisions.py`. Leave these files as given:

| File | Already done for you |
|---|---|
| `src/contracts.py` | Proposal shape, identities, evidence, settings, and `failed()` |
| `src/planner.py` | Fake model. It never calls a provider. |
| `src/graph.py` | The six nodes and the routes between them |
| `main.py` | Prints the report after you finish the decisions |
| `DECISIONS.md` | The six decisions, in the order the graph uses them |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

Copy `.env.example` to `.env` only if you later try a live model on your own. This assignment does not read a provider key. `.env` must not be committed.

## The path through the graph

Read `src/graph.py` once before you write code. The nodes run in this order:

1. `read_case` calls `check_access`. A refusal stops the workflow. The model is not called.
2. `reserve` calls `reserve_call`. This admits one model call, or stops for the call limit or the token budget.
3. `propose` asks the fake planner for a `Proposal`.
4. If the proposal is not `create_review_task`, the graph returns to `reserve`. That is the investigate loop.
5. `validate` calls `validate_proposal`. A bad invoice stops here. No task is written.
6. `approval` pauses with `interrupt`. The question is `Approve this billing review task?`
7. After a person resumes, `approval` calls `approval_decision`.
8. Only an approved result reaches `execute`, which calls `action_key` and `TaskLedger.create`.

`main.py` starts as the analyst, prints the paused review, then resumes as the manager.

## Worked values

Use case `SF-1042`, invoice `SAP-8841`, tenant `acme-in`, and request `request-1`.

The default settings are:

| Setting | Value | Meaning |
|---|---|---|
| `max_model_calls` | 3 | After three admitted calls, the next admission is `ITERATION_LIMIT`. |
| `reserve_tokens` | 2000 | Every admitted call reserves 2000 tokens before the model runs. |
| `total_token_budget` | 6000 | A reservation that would pass 6000 is `TOKEN_BUDGET`. |
| `approval_ttl_seconds` | 900 | Approval stays open for 900 seconds from the clock used when the review starts. |

One happy proposal uses 1 call and reserves 2000 tokens. The fake planner reports 240 tokens. Reported usage does not give the reservation back.

The loop scenario keeps proposing `investigate`. The workflow admits call 1, call 2, and call 3, then the fourth admission returns `ITERATION_LIMIT`. `model_calls` stays 3 and `reserved_tokens` stays 6000. No task is created.

If the budget is only 2000, call 1 is admitted and call 2 returns `TOKEN_BUDGET`. `model_calls` stays 1.

`load_settings({"max_model_calls": 0})` raises `ValueError` and the message contains `at least 1`. `load_settings({})` keeps the defaults.

## Identities

These principals are in `DIRECTORY`. Do not invent a login system.

| Name | Tenant | Permissions | Expected result |
|---|---|---|---|
| analyst | acme-in | `case:read` | May start the case. May not approve. |
| manager | acme-in | `case:read`, `task:approve`, `task:write` | May approve the exact proposal. |
| viewer | acme-in | none | `ACCESS_DENIED` before a model call. |
| outsider | other-co | all three permissions | `ACCESS_DENIED`, because the tenant differs. |

Knowing the thread id is not permission to read the case.

## Proposal check

`validate_proposal` returns `None` only when every line below is true:

- `action` is `create_review_task`
- `case_id` is `SF-1042`
- `invoice_id` is `SAP-8841`
- both identifiers are inside `evidence_refs`

The wrong-invoice scenario proposes `SAP-9999`. That is `EVIDENCE_MISMATCH`. The customer sentence "refund me now" remains in the evidence description. It does not change the invoice and it does not authorize a refund. `refund_now` is not a valid `Proposal` action. The fake planner repairs that scenario on the second call: 2 calls, 4000 reserved tokens, 480 reported tokens, then the review pause.

## Approval

`approval_decision` checks the reply in this order:

1. `approved` is a boolean. `"yes"` is `INVALID_APPROVAL`.
2. `proposal_hash` equals the hash of this proposal. A different hash is `STALE_APPROVAL`.
3. The current principal has `task:approve` and the same tenant. The analyst is `APPROVAL_FORBIDDEN`.
4. `now` is still before `expires_at`. A clock at 1000 and a later clock at 2000 is `APPROVAL_EXPIRED`, because the window closed at 1900.
5. `True` approves and records `approved_by` as the principal's subject, which is `manager`.
6. `False` is a rejection. The status becomes `rejected` and the ledger stays empty.

## One task identity

`action_key("acme-in", "request-1", proposal_hash)` returns `acme-in:request-1:<hash>`.

`TaskLedger.create` remembers that key:

- The same key and the same payload returns the original receipt. `all()` still has one row.
- The same key and a different payload raises `ValueError` whose message contains `payload`.
- The first new key returns `{"action_key": key, "task_id": "TASK-1"}`.

A rejection or a failed check does not call `create`.

## What `python main.py` prints

```text
=== BILLING REVIEW REPORT ===
Case: SF-1042
Invoice: SAP-8841
Status before approval: review
Tasks before approval: 0
Model calls: 1
Status after approval: completed
Approved by: manager
Tasks after approval: 1
```

## Checks

The grader runs 11 checks offline. Pass mark is 80 percent, which is at least 9 checks. A perfect score is 20 portal points. A lower score receives the same fraction of 20. A later run updates the score only when it is higher.

1. The repository contains the given files, the decision sheet, and a finished `learner_decisions.py`.
2. A viewer and an outsider are denied before a model call.
3. The analyst run pauses for approval, and the manager creates one task.
4. A manager rejection creates no task.
5. The wrong invoice is `EVIDENCE_MISMATCH`.
6. The investigate loop stops at three calls.
7. A 2000-token budget stops the second call, and a zero call limit is refused by `load_settings`.
8. `"yes"` and a different proposal hash are refused.
9. The analyst cannot approve, and an expired window is refused.
10. The same action key does not create a second task, and the malformed proposal is repaired on the second call.
11. `python main.py` prints the report above.

## Submit

Push the contents of `billing-review/` as the repository root. Do not push the parent folder as the only top-level directory.

Use the assignment desk: https://assignments.worker2builder.ai

Select **OCT2 - Billing Review Harness**. Use the email on your learner portal. Tests run only when that email belongs to this cohort.

## Reflection

Answer these three questions in this README, in a short paragraph each:

1. Why does the model draft the summary while validate_proposal checks the invoice?

The model is useful for interpreting the available evidence and drafting a human-readable summary of the suspected duplicate renewal charge. However, model-generated content is not automatically trustworthy. The validate_proposal function acts as a deterministic control boundary: it checks that the proposed case ID and invoice ID match the trusted evidence. This separates flexible language generation from critical business validation and prevents the model from introducing unsupported invoice references.

2. Why is the approver taken from the current principal instead of from the proposal text?

The approver must be identified from the authenticated current principal because authorization is an identity and permissions decision, not a decision the model can make. Proposal text is untrusted input and could contain a fabricated approver name. Using the current principal allows the workflow to verify tenant membership and the task:approve permission before accepting the approval.

3. Why does the same action key return the existing receipt instead of creating another task?

The same action key represents the same intended business action. Returning the existing receipt makes task creation idempotent: if the workflow retries after an interruption or an uncertain response, it does not create a duplicate review task. The ledger also checks that the payload matches the original request, preventing the same key from being reused for a different action.
