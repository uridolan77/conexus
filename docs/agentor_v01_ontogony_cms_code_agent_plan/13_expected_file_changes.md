# 13 — Expected File Changes

Likely files to modify:

```text
agentor/app/models.py
agentor/app/executor.py
agentor/app/clients/tool.py
agentor/app/workflows/ontogony_cms.py
agentor/tests/test_executor.py
agentor/tests/test_ontogony_workflow.py
agentor/tests/test_tool_client.py
agentor/README.md
```

Optional new files:

```text
agentor/app/cms/__init__.py
agentor/app/cms/ontogony.py
agentor/app/utils/json_response.py
agentor/examples/run_ontogony_cms.py
agentor/tests/test_cms_formatter.py
agentor/tests/test_json_response.py
```

Avoid modifying unless required:

```text
backend/
frontend/
docs/conexus_agentor_plan_package/
```

Reason: current task is Agentor v0.1 workflow implementation, not Conexus core.
