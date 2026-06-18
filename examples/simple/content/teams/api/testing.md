# API Team Testing Conventions

This overrides the org-level testing.md for API team repos.

## Coverage Requirements

- Unit test coverage minimum: 90% (stricter than org default of 80%)
- Contract tests required for all inter-service APIs
- Load tests required for endpoints with >100 RPS

## API-Specific Testing

- Use httpx for async API testing
- Mock external services at the HTTP boundary, not at the client level
- Test all error codes, not just the happy path
