# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

sdlc-mcp: an open-source MCP server that serves hierarchical organizational context to AI agents. The server resolves a configurable hierarchy of named scopes, reads content from pluggable sources (local directories, git repos), merges with "most specific wins" semantics, and serves the result via MCP tools.

See [docs/design.md](docs/design.md) for the full design document.

## Commands

```bash
# Dependencies
uv sync

# Run the server (stdio, default)
uv run sdlc-mcp serve

# Run as HTTP server with Google OAuth
export GOOGLE_CLIENT_ID="…"
export GOOGLE_CLIENT_SECRET="…"
export SDLC_MCP_BASE_URL="https://your-server.run.app"
uv run sdlc-mcp serve --transport streamable-http --port 8000

# Lint
uvx ruff check .
uvx ruff format .

# Tests
uv run pytest
```

## Architecture

**Config loading:** A config file is a YAML list of named scopes. Each scope has a `name`, optional `sources`, optional `repos` filter, optional `strategy`, and optional `include` list of `file://` or `git+<url>` URIs. Scopes are processed top to bottom. Includes are resolved recursively before the including scope, so included content is the base and later scopes override. If `--config` is not specified, config is loaded from: `SDLC_MCP_CONFIG` env var, `/etc/sdlc-mcp/config.yml`, or `~/.config/sdlc-mcp/config.yml`.

**Hierarchy resolution:** Given a repo identifier, filter scopes to those that apply (no `repos` filter, or repo name matches). The org prefix is stripped, so `ansible/awx` and `shanemcd/awx` both match a scope with `repos: [awx]`.

**Content sources:** Pluggable adapters that read markdown files. `local` reads from a directory. `git` clones a repo and reads from a path within it.

**Scope resolution:** A scope matches a repo three ways: no `repos` filter (matches all), repo name in `repos` list, or repo name equals scope name. All matching scopes stack in config order. The org prefix is stripped (`ansible/awx` → `awx`).

**Merging:** Configurable per-scope via `strategy` field (default: `overwrite`). Four strategies:
- `overwrite` — full file replacement (default, backwards compatible)
- `append` — concatenate after existing content
- `merge-append` — append under matching markdown heading paths (hierarchical: `## > ###` matters). Appended content is prefixed with `scope specific overrides:` for attribution. Unmatched sections are appended at the end of the document.
- `template` — fill `{NAME}` placeholders with `@NAME` blocks. Sigils: `{FOO}` (first filler wins), `{!FOO}` (last filler wins), `{?FOO}` (first filler, strip if unfilled), `{!?FOO}` (last filler, strip if unfilled)

The first scope to provide a file is always the base. Strategy only applies to subsequent scopes. Different scopes can use different strategies for the same file.

**MCP tools:** Content tools are auto-generated from markdown frontmatter (one tool per artifact).

**Source layout:**

```
src/sdlc_mcp/
  __main__.py        # CLI entry point
  server.py          # FastMCP server + dynamic tool registration
  config.py          # Config loading, include resolution, scope merging
  hierarchy.py       # Hierarchy resolution engine
  repo.py            # Shared git clone/cache helpers
  sources/           # Pluggable content source adapters
    __init__.py      # Source protocol + frontmatter parsing
    local.py         # Local directory source
    git.py           # Git repo source
  merge.py           # Content merging with pluggable strategies
  discovery.py       # Repo and tool discovery (list_repos, list_tools_for_repo)
```

## Conventions

- Use `uv` for all Python package management
- Use proper `logging` module, never `print()`
- Source code under `src/sdlc_mcp/`
- Examples under `examples/`
- The server must be org-agnostic. No hardcoded references to any specific organization or tool. All org-specific knowledge comes from config and content.
- Config format is YAML
- Content sources are markdown files
- Use `fastmcp` (https://gofastmcp.com) for the MCP server, not the low-level `mcp` SDK. Import as `from fastmcp import FastMCP`. See https://gofastmcp.com/llms-full.txt for full API reference.

## Authentication

Google OAuth is supported via FastMCP's built-in `GoogleProvider`. It activates automatically when `GOOGLE_CLIENT_ID` is set. Required env vars:

- `GOOGLE_CLIENT_ID` — OAuth2 client ID from GCP Console
- `GOOGLE_CLIENT_SECRET` — corresponding client secret
- `SDLC_MCP_BASE_URL` — public URL of the server (e.g. `https://your-server.run.app`)

The authorized redirect URI in GCP Console must be set to `<SDLC_MCP_BASE_URL>/auth/callback`. When env vars are absent, auth is disabled and the server runs unauthenticated (suitable for local stdio usage).

## Implementation Status

Phases 1-3.5 are complete (skeleton, git source, real content, discovery tools, merge strategies). Config includes, dynamic tool registration from frontmatter, the scope-based config model, pluggable merge strategies, and discovery tools are all implemented. See docs/design.md for the full design.
