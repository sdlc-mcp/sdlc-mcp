# Extending sdlc-mcp

sdlc-mcp is org-agnostic by design. All organizational knowledge comes from config and content files, not from the server code. The recommended way to deliver your organization's context to AI agents is to create a **wrapper package** — a Python project that depends on `sdlc-mcp`, bundles your config and content, and ships as its own MCP server.

## Why a Wrapper Package

- **Single install:** `pip install my-org-mcp` gives your team everything they need.
- **Auto-discovery:** The `context_version` tool automatically detects and reports installed wrapper packages.
- **Private content stays private:** Your organizational standards, team conventions, and internal processes live in your own repo, not upstream.
- **Independent versioning:** Ship content updates on your own schedule without waiting for sdlc-mcp releases.

## Directory Structure

```
my-org-mcp/
  pyproject.toml              # Package metadata, depends on sdlc-mcp
  src/
    my_org_mcp/
      __init__.py             # Empty
      __main__.py             # CLI entry point
  config.yml                  # Scope hierarchy
  context-metadata.yml        # Name, version, and other metadata
  content/
    org/                      # Org-wide content (applies to all repos)
      code-review.md
      testing.md
    teams/
      api/                    # Team-specific content
        testing.md
      frontend/
        testing.md
  Makefile
  README.md
  .gitignore
```

Conventions:
- Package name uses hyphens (`my-org-mcp`), importable module uses underscores (`my_org_mcp`).
- `config.yml` and `context-metadata.yml` sit at the project root, alongside `pyproject.toml`.
- Content files go under `content/`, organized by scope: `org/` for org-wide, `teams/<name>/` for team-specific.

## pyproject.toml

```toml
[project]
name = "my-org-mcp"
dynamic = ["version"]
description = "MCP server delivering My Org context to AI agents"
requires-python = ">=3.11"
dependencies = [
    "sdlc-mcp",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
my-org-mcp = "my_org_mcp.__main__:main"

[tool.uv]
package = true

[build-system]
requires = ["setuptools>=64", "setuptools-scm>=8"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools_scm]
version_scheme = "calver-by-date"

[tool.ruff]
line-length = 100
target-version = "py311"
```

Key points:
- `dependencies = ["sdlc-mcp"]` is what makes auto-discovery work. The `context_version` tool scans installed packages for this dependency.
- The `[project.scripts]` entry point lets you run `my-org-mcp serve` from the command line.
- CalVer via `setuptools-scm` matches the upstream versioning convention.

## Entry Point

The wrapper's `__main__.py` imports from `sdlc_mcp.server` and points it at your bundled config:

```python
"""CLI entry point for my-org-mcp."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="my-org-mcp",
        description="MCP server for My Org context",
    )
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the MCP server")
    serve_parser.add_argument(
        "--config",
        type=Path,
        action="append",
        default=None,
        help="Path to config file (default: bundled config.yml)",
    )
    serve_parser.add_argument("--repo-path", type=Path, default=None)
    serve_parser.add_argument("--verbose", "-v", action="store_true")
    serve_parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
    )
    serve_parser.add_argument("--host", default="localhost")
    serve_parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "serve":
        logging.basicConfig(
            level=logging.DEBUG if args.verbose else logging.INFO,
            format="%(name)s - %(levelname)s - %(message)s",
        )

        from sdlc_mcp.server import init_config_from_path, mcp

        config_paths = args.config or [_PACKAGE_ROOT / "config.yml"]
        init_config_from_path(config_paths=config_paths, repo_path=args.repo_path)
        if args.transport == "stdio":
            mcp.run(transport="stdio")
        else:
            mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
```

`_PACKAGE_ROOT` resolves from `src/my_org_mcp/__main__.py` up three levels to the project root where `config.yml` lives. This works in development mode (`pip install -e .`). For production installs, pass `--config` explicitly or set the `SDLC_MCP_CONFIG` environment variable.

## Config File

The config file is a YAML list of named scopes, processed top to bottom. Each scope points at content sources and optionally filters by repo name.

```yaml
- name: my-org
  sources:
    - type: local
      path: content/org/

- name: api
  repos: [api-gateway, api-auth]
  sources:
    - type: local
      path: content/teams/api/

- name: frontend
  repos: [web-app, design-system]
  strategy: merge-append
  sources:
    - type: local
      path: content/teams/frontend/
```

- Scopes without `repos` apply to all repos (org-wide baseline).
- Scopes with `repos` only apply when the requested repo matches.
- `strategy` controls how team content merges with org content: `overwrite` (default), `append`, or `merge-append`.
- `vars` can be added to any scope for Jinja2 template rendering.
- `include` can pull in external configs via `file://` or `git+<url>` URIs.

Relative paths in `sources` resolve from the config file's parent directory.

## Content Files

Each markdown file becomes an MCP tool. Use YAML frontmatter to set the tool name and description:

```markdown
---
name: code-review
description: "How code reviews should be conducted: methodology, scoring, and approval"
---

# Code Review Standards

## Pull Request Requirements

- PRs should be focused on a single concern
- Include a description of what changed and why
...
```

- `name` becomes the MCP tool name (hyphens are converted to underscores).
- `description` is what agents see when they list available tools.
- Without frontmatter, the filename (minus `.md`) becomes the tool name and the first heading becomes the description.

## Context Metadata

Place a `context-metadata.yml` alongside `config.yml` with flat key/value pairs:

```yaml
name: my-org-engineering-standards
version: 1.0.0
maintainer: platform-team@my-org.com
```

The `context_version` tool reports these values (prefixed with `context_`) alongside the sdlc-mcp engine version and your wrapper package version.

## Auto-Discovery

When your wrapper package is installed, `sdlc-mcp` automatically detects it. The `context_version` tool scans all installed Python distributions for packages that list `sdlc-mcp` in their dependencies and reports their name and version. No registration step is needed — the dependency in `pyproject.toml` is the only integration point.

## Running and Testing

Install in development mode:

```bash
cd my-org-mcp
uv sync
uv pip install -e .
```

Run the server:

```bash
my-org-mcp serve
```

Verify tools are registered:

```bash
uv run fastmcp list --command "uv run my-org-mcp serve"
```

Register with Claude Code:

```bash
claude mcp add --transport stdio --scope project my-org-mcp \
  -- uvx my-org-mcp serve
```

## Scaffolding Shortcut

To generate a complete wrapper package with all the boilerplate:

```bash
# From the sdlc-mcp repo
make new-project NAME=my-org-mcp ORG="My Org" TEAMS="api,frontend,data"
```

This creates the full directory structure, ready to customize and run. See the generated `README.md` for next steps.
