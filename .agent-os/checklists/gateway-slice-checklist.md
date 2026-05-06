# Gateway Slice Checklist

Use this before landing a Conexus gateway or provider-adapter change.

- The slice improves a real request path, not just framework shape.
- The owning docs were checked: scope, architecture, provider abstraction, and REASONS if needed.
- Provider SDK details stay inside adapter or mapper code.
- Request validation, routing, normalization, and trace logging boundaries are still clear.
- Success and failure paths both preserve trace visibility.
- The change was validated with the narrowest relevant backend or end-to-end check.
- Any contract or behavior change was reflected in docs in the same slice.
