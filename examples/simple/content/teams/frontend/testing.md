# Frontend Team Testing Conventions

This overrides the org-level testing.md for frontend team repos.

## Coverage Requirements

- Unit test coverage minimum: 75% (relaxed from org default for UI code)
- Visual regression tests required for all component changes
- Accessibility tests required for all user-facing components

## Frontend-Specific Testing

- Use Playwright for end-to-end tests
- Use Testing Library for component tests
- Snapshot tests are discouraged; prefer behavioral assertions
