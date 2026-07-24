# Debug sdlc-mcp Hierarchy Resolution

This skill helps you debug which content an agent receives for a specific repo.

## When to use

- A repo is getting the wrong content (or no content)
- You're not sure which scope is "winning" for a given file
- Merge strategy isn't producing expected results

## Steps

1. **Check scope matching** — Run `list_tools_for_repo` with the repo name:

```bash
make call-pretty TOOL=list_tools_for_repo ARGS='{"repo": "<repo-name>"}'
```

This shows each tool, which scope provides it, and which scopes were overridden.

2. **Check the config** — Verify the repo name appears in the correct team scope's `repos` list. Remember: org prefix is stripped (`ansible/awx` matches `repos: [awx]`).

3. **Check scope order** — Scopes are processed top to bottom in `config.yml`. The last matching scope wins (for `overwrite` strategy). Verify the order is: org-wide first, then team-specific.

4. **Check merge strategy** — If using `append` or `merge-append`, verify the team scope has the correct `strategy` field. The default is `overwrite`.

5. **Check content files** — Verify the markdown files exist in the expected directories and have valid frontmatter.

6. **Check includes** — If using `include` directives, verify the URIs are accessible and the included config is valid YAML.

## Common issues

- **Missing content:** The repo name doesn't match any team scope's `repos` list. Org-wide content still applies.
- **Wrong version of a file:** Check scope order — a later scope with the same file will overwrite an earlier one.
- **Partial content:** If using `merge-append`, ensure heading structures match between org and team files.
