---
name: testing
description: "Testing standards and conventions"
---
# Testing Standards

## Coverage
Unit test coverage minimum: 80%.
Integration tests required for all API endpoints.

## Naming
Use test_ prefix for all test functions.
Group tests by module under tests/ directory.

## CI
Run all tests before merging.
PRs with failing tests must not be merged.
