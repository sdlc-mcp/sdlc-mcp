---
name: testing
description: "Testing standards and conventions"
---
# Testing Standards

## Coverage
All teams must achieve {{ coverage_target | default("80%") }} code coverage.
Integration tests required for all API endpoints.

## Naming
Use test_ prefix for all test functions.
Group tests by module under tests/ directory.

## CI
Run all tests before merging.
PRs with failing tests must not be merged.

{% if team_testing_notes %}
## Team-Specific Notes
{{ team_testing_notes }}
{% endif %}
