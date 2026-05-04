from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import models


async def test_m5_metadata_contains_usage_alias_and_key_columns() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

            def _inspect(sync_conn):
                inspector = inspect(sync_conn)
                return {
                    "tables": set(inspector.get_table_names()),
                    "project_api_keys": {
                        column["name"]
                        for column in inspector.get_columns("project_api_keys")
                    },
                    "usage_events": {
                        column["name"] for column in inspector.get_columns("usage_events")
                    },
                    "usage_event_unique_constraints": {
                        constraint["name"]
                        for constraint in inspector.get_unique_constraints("usage_events")
                    },
                    "gateway_model_aliases": {
                        column["name"]
                        for column in inspector.get_columns("gateway_model_aliases")
                    },
                }

            schema = await conn.run_sync(_inspect)
    finally:
        await engine.dispose()

    assert "usage_events" in schema["tables"]
    assert "gateway_model_aliases" in schema["tables"]
    assert "last_used_at" in schema["project_api_keys"]
    assert {
        "gateway_request_id",
        "project_id",
        "provider",
        "model",
        "requested_model",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cost_usd",
        "metadata_json",
    } <= schema["usage_events"]
    assert (
        "uq_usage_events_gateway_request_id"
        in schema["usage_event_unique_constraints"]
    )
    assert {
        "alias",
        "primary_provider",
        "primary_model",
        "fallback_provider",
        "fallback_model",
        "status",
        "metadata_json",
    } <= schema["gateway_model_aliases"]
