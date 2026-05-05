# 14 — Definition of Done

Agentor v0.1 is done when:

```text
Given a topic or page brief,
the workflow plans an Ontogony essay,
optionally reads sources through ToolClient,
drafts with Conexus,
critiques with structured scores,
formats Astro/Tina-compatible MDX,
and pauses for human approval before any write.
```

Hard acceptance:

```bash
cd agentor
pytest
```

Manual acceptance:

```python
workflow = OntogonyCmsWorkflow(conexus=mock_or_real_client, tool=tool)
run = await workflow.run("Closure-Crisis Lemma", auto_approve=False)

assert run.status == RunStatus.AWAITING_APPROVAL
assert run.state.get("cms_output")
assert run.state.get("target_path").startswith("src/content/essays/")
assert run.checkpoint is not None
```

Before approval:
- no files written
- no PR opened
- run awaiting approval

After approval:
- v0.1 may only return approved run
- actual write/PR is v0.2 unless specifically implemented behind approval
