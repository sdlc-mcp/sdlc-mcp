"""Generate a wrapper package that extends sdlc-mcp."""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _validate_name(name: str) -> str:
    if not re.match(r"^[a-z][a-z0-9-]*$", name):
        raise argparse.ArgumentTypeError(
            f"Invalid project name {name!r}. "
            "Use lowercase letters, digits, and hyphens (e.g. 'my-org-mcp')."
        )
    return name


def _to_package_name(name: str) -> str:
    return name.replace("-", "_")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    logger.info("Created %s", path)


def scaffold(name: str, org: str, teams: list[str], output_dir: Path) -> Path:
    """Create a complete wrapper package directory.

    Returns the path to the created project directory.
    """
    project_dir = output_dir / name
    if project_dir.exists():
        logger.error("Directory %s already exists. Aborting.", project_dir)
        sys.exit(1)

    package_name = _to_package_name(name)
    scope_name = name.removesuffix("-mcp") if name.endswith("-mcp") else name

    # pyproject.toml
    _write(
        project_dir / "pyproject.toml",
        f"""\
[project]
name = "{name}"
dynamic = ["version"]
description = "MCP server delivering {org} organizational context to AI agents"
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
{name} = "{package_name}.__main__:main"

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
""",
    )

    # src/<package>/__init__.py
    _write(project_dir / "src" / package_name / "__init__.py", "")

    # src/<package>/__main__.py
    _write(
        project_dir / "src" / package_name / "__main__.py",
        f'''\
"""CLI entry point for {name}."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="{name}",
        description="MCP server for {org} organizational context",
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
''',
    )

    # config.yml
    team_scopes = ""
    for team in teams:
        team_scopes += f"""
- name: {team}
  repos: []
  sources:
    - type: local
      path: content/teams/{team}/
"""
    _write(
        project_dir / "config.yml",
        f"""\
# {org} SDLC context configuration
# Scopes are processed top to bottom. Later scopes override earlier ones.
# Add repo names to each team's `repos` list to scope content to those repos.

- name: {scope_name}
  sources:
    - type: local
      path: content/org/
{team_scopes}""",
    )

    # context-metadata.yml
    _write(
        project_dir / "context-metadata.yml",
        f"""\
name: {name}
version: 0.1.0
""",
    )

    # content/org/code-review.md
    _write(
        project_dir / "content" / "org" / "code-review.md",
        f"""\
---
name: code-review
description: "How code reviews should be conducted at {org}"
---

# Code Review Standards

## Pull Request Requirements

- PRs should be focused on a single concern
- Include a description of what changed and why
- Link to the relevant issue or ticket

## Review Process

- Reviewers should respond within one business day
- Approve when all blocking issues are resolved
""",
    )

    # content/org/testing.md
    _write(
        project_dir / "content" / "org" / "testing.md",
        f"""\
---
name: testing
description: "Testing standards and conventions at {org}"
---

# Testing Strategy

## Coverage Requirements

- Unit test coverage minimum: 80%
- Integration tests required for all API endpoints
- End-to-end tests required for critical user flows

## Test Organization

- Tests live alongside source code in a `tests/` directory
- Use factories over fixtures for test data
""",
    )

    # content/teams/<team>/testing.md for each team
    for team in teams:
        team_title = team.replace("-", " ").title()
        _write(
            project_dir / "content" / "teams" / team / "testing.md",
            f"""\
---
name: testing
description: "{team_title} team testing conventions"
---

# {team_title} Testing

Add team-specific testing conventions here.
This file overrides the org-level testing.md for repos in this team's scope.
""",
        )

    # Makefile
    _write(
        project_dir / "Makefile",
        f"""\
SDLC_MCP_CONFIG ?= ./config.yml

.PHONY: help install serve serve-http lint format list-tools

help: ## Show available targets
\t@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {{FS = ":.*?## "}}; {{printf "  \\033[36m%-25s\\033[0m %s\\n", $$1, $$2}}'

install: ## Install locally
\tuv sync
\tuv pip install -e .
\t@uv run python -c "from importlib.metadata import version; print('{name}:', version('{name}'))"

serve: ## Run server via stdio
\tSDLC_MCP_CONFIG=$(SDLC_MCP_CONFIG) uv run {name} serve

serve-http: ## Run server via HTTP on localhost:8000
\tSDLC_MCP_CONFIG=$(SDLC_MCP_CONFIG) uv run {name} serve --transport streamable-http --host localhost --port 8000

lint: ## Run linter and format check
\tuvx ruff check .
\tuvx ruff format --check .

format: ## Auto-format code
\tuvx ruff format .

list-tools: ## List all registered tools
\tuv run fastmcp list --command "uv run {name} serve --config $(SDLC_MCP_CONFIG)"
""",
    )

    # README.md
    _write(
        project_dir / "README.md",
        f"""\
# {name}

MCP server delivering {org} organizational context to AI agents, built on [sdlc-mcp](https://github.com/shanemcd/sdlc-mcp).

## Quick Start

```bash
make install
make serve
```

## Register with Claude Code

```bash
claude mcp add --transport stdio --scope project {name} \\
  -- uvx {name} serve
```

## Project Structure

- `config.yml` — scope hierarchy defining which content applies to which repos
- `context-metadata.yml` — package metadata reported by the `context_version` tool
- `content/org/` — org-wide content (applies to all repos)
- `content/teams/<team>/` — team-specific content (scoped by `repos` filter)

## Adding Content

1. Create a markdown file in `content/org/` or `content/teams/<team>/`
2. Add YAML frontmatter with `name` and `description`
3. The file automatically becomes an MCP tool

```markdown
---
name: deployment
description: "How to deploy services"
---

# Deployment Guide
...
```

## Adding a Team

Add a new scope to `config.yml`:

```yaml
- name: data-layer
  repos: [db-service, data-pipeline]
  sources:
    - type: local
      path: content/teams/data-layer/
```

Then create `content/teams/data-layer/` with markdown files.

## Docs

- [Extending sdlc-mcp](https://github.com/shanemcd/sdlc-mcp/blob/main/docs/extending.md) — full reference
""",
    )

    # .gitignore
    _write(
        project_dir / ".gitignore",
        """\
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.venv/
.cache/
""",
    )

    logger.info("Project created at %s", project_dir)
    return project_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a wrapper package that extends sdlc-mcp",
    )
    parser.add_argument(
        "--name",
        type=_validate_name,
        required=True,
        help="Project name (e.g. my-org-mcp)",
    )
    parser.add_argument(
        "--org",
        default=None,
        help="Organization display name (default: derived from project name)",
    )
    parser.add_argument(
        "--teams",
        default="api,frontend",
        help="Comma-separated team names (default: api,frontend)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Parent directory for the new project (default: current directory)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    org = args.org or args.name.removesuffix("-mcp").replace("-", " ").title()
    teams = [t.strip() for t in args.teams.split(",") if t.strip()]

    scaffold(args.name, org, teams, args.output_dir)


if __name__ == "__main__":
    main()
