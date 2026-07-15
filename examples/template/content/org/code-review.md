---
name: code-review
description: "Code review standards and process"
---
# Code Review Standards

## Pull Request Requirements
PRs should be focused on a single concern.
Include a description of what changed and why.
Link to the relevant issue or ticket.
{% if team_pr_requirements %}
{{ team_pr_requirements }}
{% endif %}

## Review Process
Reviewers should respond within one business day.
Use "request changes" for blocking issues, "comment" for suggestions.
Approve when all blocking issues are resolved.

## Merge Policy
Squash merge to main.
Delete the branch after merging.
