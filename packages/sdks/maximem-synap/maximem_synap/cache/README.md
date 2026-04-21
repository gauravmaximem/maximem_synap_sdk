# SDK Cache

## What belongs here
- Client-side caching strategies
- Cache key generation
- TTL and eviction policies
- Local storage mechanisms

## What must NEVER belong here
- Server-side caching
- Provider-specific caching
- Business logic
- Authentication
- Network transport

## Dependencies
- May depend on: Nothing (within sdk/python)
- Must NOT depend on: core, cloud, providers, contracts
