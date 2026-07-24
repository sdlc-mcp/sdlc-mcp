# Add Content to an sdlc-mcp Wrapper

This skill helps you add new content files to an existing sdlc-mcp wrapper package.

## What this does

Adds a new markdown content file that becomes an MCP tool. The file is placed in the appropriate scope directory (org-wide or team-specific) and includes YAML frontmatter for tool registration.

## Steps

1. **Identify the scope** — Is this org-wide content (applies to all repos) or team-specific?
2. **Choose a name** — The filename (without `.md`) becomes the tool name. Use kebab-case (e.g., `deployment-guide.md`).
3. **Write the content** — Create the markdown file with frontmatter:

```markdown
---
name: deployment-guide
description: "How to deploy services to production"
---

# Deployment Guide

Your content here...
```

4. **Place the file** — Put it in:
   - `content/org/` for org-wide content
   - `content/teams/<team>/` for team-specific content

5. **Verify** — Run `make list-tools` to confirm the new tool appears.

## Notes

- If a team-specific file has the same name as an org file, the merge strategy on that team's scope determines what happens (overwrite, append, or merge-append).
- Hyphens in filenames are converted to underscores in tool names (`deployment-guide.md` → `deployment_guide` tool).
