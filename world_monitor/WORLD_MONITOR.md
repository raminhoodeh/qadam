# World Monitor Adapter Rules

Every source adapter must:

1. Read credentials from environment or the local secret provider.
2. Return raw payloads without mutating them.
3. Emit normalized event candidates using the shared event shape.
4. Record latency, source status, and rate-limit state.
5. Fail closed when data is stale, malformed, or contradicted by a higher-trust source.

## Unified Event Shape

- `source`
- `source_type`
- `event_type`
- `observed_at`
- `ingested_at`
- `coordinates`
- `normalised_summary`
- `raw_payload`
- `trust_score_at_collection`

## Source Status

- `ready_to_port`: World Monitor has usable implementation patterns.
- `needs_new_adapter`: Specs define the source, but World Monitor does not implement it.
- `needs_clarity`: Specs conflict or omit endpoint details.
- `local_bridge`: Requires a local process.
- `derived`: Internal aggregation layer.

