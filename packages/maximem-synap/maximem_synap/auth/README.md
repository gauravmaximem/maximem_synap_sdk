# SDK Auth

## What belongs here
- API key management
- Token refresh logic
- Credential storage (client-side)
- Auth header construction

## What must NEVER belong here
- Token verification or validation
- User management
- Authorization policies
- Session management
- Multi-tenancy logic

## Dependencies
- May depend on: Nothing (within sdk/python)
- Must NOT depend on: core, cloud, providers, contracts
