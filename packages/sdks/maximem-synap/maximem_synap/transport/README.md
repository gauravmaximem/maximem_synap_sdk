# SDK Transport

## What belongs here
- HTTP client implementations
- Request serialization and deserialization
- Retry and timeout logic
- Connection pooling

## What must NEVER belong here
- Business logic
- Core algorithms
- Authentication token generation
- Cache invalidation rules
- Provider implementations

## Dependencies
- May depend on: auth, cache (within sdk/python)
- Must NOT depend on: core, cloud, providers
