# SDK Facade

## What belongs here
- Public client API surface
- Developer-facing method signatures
- Configuration objects
- Input validation and sanitization

## What must NEVER belong here
- HTTP transport implementation
- Core algorithm implementations
- Provider-specific logic
- Cloud application logic
- Direct database operations

## Dependencies
- May depend on: transport, cache, auth (within sdk/python)
- Must NOT depend on: core, cloud, providers (indirectly via transport)
