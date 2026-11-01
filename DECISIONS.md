# Billing review decisions

These are the class decisions this assignment asks you to implement. The graph already calls them in order.

| Decision | Where it lives | What the code must do |
|---|---|---|
| The model drafts a proposal. It does not write a task. | `propose`, then `execute` | A task appears only after approval. |
| Invoice facts come from the evidence, not from a convincing summary. | `validate_proposal` | A different invoice id is `EVIDENCE_MISMATCH`. |
| Another tenant cannot read the case, even with a thread id. | `check_access` | Wrong tenant or missing `case:read` is `ACCESS_DENIED` before a model call. |
| The application admits each model call. | `reserve_call` | Stop at the call limit and the token budget. |
| Approval is bound to the exact proposal and the current person. | `approval_decision` | Boolean approval, matching hash, `task:approve`, and an open window. |
| One approved action has one identity. | `action_key` and `TaskLedger.create` | The same key returns the same receipt. A different payload is refused. |

Customer text such as "refund me now" stays inside the evidence description. It is data. It is not an instruction and it is not a permission.
