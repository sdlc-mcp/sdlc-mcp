# sdlc-mcp

An open-source MCP server that gives AI agents a table of contents for your organization.

## Why

AI agents need organizational knowledge to do real work: how to write a Jira story, how code reviews are conducted, what the testing standards are. This knowledge exists at different levels (org-wide, team-specific, repo-specific) and some of it can't live in public repos.

Putting everything in CLAUDE.md doesn't scale across repos. Loading everything upfront wastes the context window. And when the agent sees both an org-level and team-level version of the same thing, it has to guess which one wins.

This server solves all three problems. Content is served on demand (the agent pulls only what it needs), managed centrally (update once, every agent gets it), and merged with a clear hierarchy (later scopes override earlier ones, so the agent only ever sees the winning version).

## How the Hierarchy Works

The config is a YAML list of named scopes, processed top to bottom. Each scope points at content sources. Scopes without a `repos` filter apply to all repos. Scopes with `repos` only apply when the requested repo matches.

```yaml
- name: acme                          # org-wide, applies to all repos
  sources:
    - type: local
      path: content/org/

- name: api                           # only applies to api-gateway, api-auth
  repos: [api-gateway, api-auth]
  sources:
    - type: local
      path: content/teams/api/
```

If both `acme` and `api` have a `testing.md`, the default behavior is that the `api` version wins for matching repos (overwrite). But you can control this with merge strategies.

Scopes can also include external configs via `file://` or `git+<url>` URIs, so content can be spread across multiple repos, public and private.

## Merge Strategies

By default, later scopes overwrite earlier ones. But sometimes you want to layer content instead of replacing it. The `strategy` field controls this per-scope:

```yaml
- name: acme                          # base — no strategy needed
  sources:
    - type: local
      path: content/org/

- name: api
  repos: [api-gateway]
  strategy: merge-append              # append under matching headings
  sources:
    - type: local
      path: content/teams/api/
```

| Strategy | What it does |
|----------|-------------|
| `overwrite` | Replaces the file entirely (default) |
| `append` | Concatenates after the existing content |
| `merge-append` | Appends under matching markdown headings (`## Testing > ### Coverage` is a distinct path from `## Deploy > ### Coverage`). Appended content is prefixed with `scope specific overrides:` for attribution. Unmatched sections are appended at the end of the document. |

### Vars (Jinja2 templates)

Scopes can declare `vars` to fill in Jinja2 expressions in content files. Vars are independent of the merge strategy and render after all merging is complete.

```yaml
- name: platform
  sources:
    - type: local
      path: content/org/

- name: api
  repos: [api-gateway]
  vars:
    coverage_target: "90%"
    team_conventions: "Contract tests required for all API endpoints."
```

```markdown
# Testing (org content file)
All teams must achieve {{ coverage_target | default("80%") }} code coverage.
{% if team_conventions %}
{{ team_conventions }}
{% endif %}
```

Vars accumulate through the hierarchy. Later scopes override earlier ones for the same key.

See the [design doc](docs/design.md) for full details on scope resolution and strategy semantics.

### Per-file strategy

Merge strategy is currently per-scope — all files in a scope use the same strategy. Per-file strategy (via frontmatter) is planned for a future release (see [Phase 3.6](docs/design.md#phase-36-per-file-merge-strategy-future) in the design doc).

As a workaround, split a team's content into multiple scopes with different strategies:

```yaml
- name: data-layer-overrides
  repos: [db-service]
  strategy: overwrite
  sources:
    - type: local
      path: content/teams/data-layer/overrides/

- name: data-layer-additions
  repos: [db-service]
  strategy: merge-append
  sources:
    - type: local
      path: content/teams/data-layer/additions/
```

## How Content Becomes Tools

Content is markdown with YAML frontmatter. Each file automatically becomes an MCP tool:

```markdown
---
name: org-structure
description: "How the organization is structured"
---

# Organization Structure
...
```

The agent sees the full table of contents the moment it connects. No CLAUDE.md hints needed. It calls the tool it needs and gets just that content.

## Quick Start

```bash
pip install sdlc-mcp
sdlc-mcp serve --config path/to/config.yml
```

Register with Claude Code:

```bash
claude mcp add --transport stdio --scope project sdlc-mcp \
  -- uvx sdlc-mcp serve --config /path/to/config.yml
```

Or bundle your config and content into a separate package that depends on `sdlc-mcp`. See the [design doc](docs/design.md) for details.

### Running as an HTTP server

```bash
sdlc-mcp serve --transport streamable-http --host localhost --port 8000 --config path/to/config.yml
```

### Content metadata

Place a `context-metadata.yml` file alongside your `config.yml` with flat key/value pairs:

```yaml
name: acme-engineering-standards
version: 2.1.0
git: https://github.com/acme/standards
maintainer: platform-team@acme.com
```

The `context_version` tool reports this metadata (prefixed with `context_`) alongside the sdlc-mcp engine version and any auto-discovered wrapper packages.

### Config lookup

If `--config` is not specified, config is loaded from these locations in order:

1. `SDLC_MCP_CONFIG` environment variable (path to config file)
2. `/etc/sdlc-mcp/config.yml` (system-wide)
3. `~/.config/sdlc-mcp/config.yml` (per-user)

### Authentication with Google OAuth

Google OAuth authentication is disabled if the following environment variables are not set. Authentication does not impact local stdio usage. For production deployments over HTTP, authentication is recommended.

```bash
export GOOGLE_CLIENT_ID="..."
export GOOGLE_CLIENT_SECRET="..."
export SDLC_MCP_BASE_URL="https://your-server.example.com"
```

When these are not set, the server runs unauthenticated over transport streamable-http.

## Docs

- [Getting Started](docs/getting-started.md) — install, run, try the examples
- [Developer Guide](docs/developer-guide.md) — project structure, testing, contributing
- [Design Doc](docs/design.md) — architecture, scope resolution, strategy semantics
- [Test Matrix](docs/merge-strategy-test-matrix.md) — full merge strategy test coverage
- [Releasing](RELEASE.md) — release process
