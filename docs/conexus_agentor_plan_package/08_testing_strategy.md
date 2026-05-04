# 08 — Testing Strategy

## Testing goals

The test suite should prove that Conexus is reliable as a gateway:

1. Provider adapters normalize responses.
2. Fallback behavior is deterministic.
3. Errors are sanitized and stable.
4. Requests are logged on success and failure.
5. Cost/usage data is accurate enough for BO visibility.
6. API key auth is correct.

## Unit tests

### Pricing

```text
test_pricing_loads_yaml
test_pricing_unknown_model_uses_conservative_fallback
test_pricing_override_json_wins
test_cost_calculation_precision
```

### Errors

```text
test_gateway_error_envelope
test_validation_error_status
test_provider_error_sanitizes_message
test_no_stack_trace_in_http_response
```

### Provider adapters

```text
test_openai_adapter_success
test_openai_adapter_missing_usage_uses_zero_or_estimate
test_openai_adapter_rate_limit_retryable
test_openai_adapter_internal_server_retryable
test_openai_adapter_auth_error_non_retryable
test_anthropic_adapter_success
test_anthropic_adapter_text_block_extraction
test_anthropic_adapter_rate_limit_retryable
test_anthropic_adapter_internal_server_retryable
test_adapter_aclose_closes_sdk_client
```

### Formatters

```text
test_openai_messages_to_anthropic_skips_system
test_tool_calls_convert_to_anthropic_tool_use
test_tool_results_group_as_user_blocks
test_openai_tool_schema_to_anthropic_tool_schema
```

### Fallback gateway

```text
test_primary_success_no_fallback
test_primary_retryable_failure_fallback_success
test_primary_non_retryable_failure_no_fallback
test_both_providers_fail_gateway_error
test_fallback_attempts_are_recorded
test_usage_from_fallback_provider_is_returned
```

### API key auth

```text
test_generate_project_key_returns_secret_once
test_verify_valid_project_key
test_revoked_key_fails
test_wrong_prefix_fails
test_key_hash_not_plaintext
```

### Request logging

```text
test_request_log_started_before_provider_call
test_request_log_completed_on_success
test_request_log_failed_on_provider_failure
test_usage_event_created_on_success
test_provider_attempts_record_fallback
```

## Integration tests

### Local DB integration

Use test Postgres or SQLite only if Postgres is too heavy initially. Prefer Postgres for schema fidelity.

```text
test_chat_completion_with_mock_provider_writes_db_rows
test_failed_chat_completion_writes_failed_request
test_admin_requests_list_returns_recent_request
test_request_detail_includes_provider_attempts
```

### Optional live provider smoke tests

Guard behind environment flags:

```text
RUN_LIVE_LLM_TESTS=1
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
```

Live tests:

```text
test_live_openai_minimal_call
test_live_anthropic_minimal_call
test_live_conexus_fast_call_under_cheap_model
```

These should not run in normal CI.

## API contract tests

```text
test_openai_compatible_response_shape
test_openai_compatible_error_shape
test_stream_true_not_supported_yet
test_client_can_call_with_base_url_and_api_key
```

## BO smoke tests

At minimum:

```text
frontend build passes
requests page renders with mocked API
request detail renders success
request detail renders failure
```

## Regression tests from KGB behavior

Copy behavior, not test structure:

- Anthropic success returns content and usage.
- Anthropic rate-limit falls back to OpenAI.
- Both providers fail raises GatewayError.
- Provider field appears in usage.
- `aclose` closes both clients and suppresses close errors.
- Cost estimate uses configured model pricing.

## CI stages

```text
backend lint
backend typecheck
backend unit tests
backend integration tests
frontend typecheck
frontend build
security audit later
```

## Acceptance definition per milestone

A milestone is not complete unless:

```text
tests pass
health endpoint works if applicable
at least one smoke command is documented
no secrets are logged
no KGB pipeline imports slipped in
```
