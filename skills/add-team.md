# Add a Team to an sdlc-mcp Wrapper

This skill helps you add a new team scope to an existing sdlc-mcp wrapper configuration.

## Steps

1. **Choose a team name** — Use kebab-case (e.g., `data-layer`, `platform`, `mobile`).

2. **Identify the repos** — Which repositories does this team own? These go in the `repos` list.

3. **Add the scope to `config.yml`**:

```yaml
- name: <team-name>
  repos: [repo-a, repo-b]
  sources:
    - type: local
      path: content/teams/<team-name>/
```

4. **Choose a merge strategy** (optional) — Add `strategy: merge-append` or `strategy: append` if the team's content should layer on top of org content rather than replacing it.

5. **Create the content directory** — `content/teams/<team-name>/`

6. **Add starter content** — At minimum, create a `testing.md` with frontmatter:

```markdown
---
name: testing
description: "<Team> team testing conventions"
---

# <Team> Testing

Team-specific testing conventions here.
```

7. **Verify** — Run `make list-tools` and check that the team's content appears for its repos.
