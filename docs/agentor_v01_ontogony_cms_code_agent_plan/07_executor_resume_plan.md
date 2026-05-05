# 07 — Executor Resume Plan

For Agentor v0.1, implement minimal approval resume.

## Required model change

`AgentRun` should include:

```python
next_node_index: int = 0
paused_at: datetime | None = None
```

## Execution behavior

When node `i` completes normally:

```python
run.next_node_index = i + 1
```

When node creates approval checkpoint and it is not decided:

```python
run.status = RunStatus.AWAITING_APPROVAL
run.paused_at = now
run.finished_at = None
run.next_node_index = i + 1
return run
```

When approval rejected:

```python
run.status = RunStatus.REJECTED
run.finished_at = now
```

When approval approved:

```python
await executor.resume(run)
```

`resume()` behavior:
- require status `AWAITING_APPROVAL`
- require checkpoint decided
- if rejected, mark rejected
- if approved, set `RUNNING` and continue from `next_node_index`
- do not re-run previous nodes

Tests:
- pauses at approval
- `finished_at` remains None while awaiting approval
- approved resume continues after approval node
- rejected resume marks rejected
- previous nodes are not re-run
