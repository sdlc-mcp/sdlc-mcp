# Developer Guide

## Setup

```bash
git clone <repo-url>
cd sdlc-mcp
make install
```

Run `make` to see all available targets.

## Project structure

```
src/sdlc_mcp/
  __main__.py        # CLI entry point
  server.py          # FastMCP server + tool registration
  config.py          # Config loading, include resolution
  hierarchy.py       # Scope resolution engine
  discovery.py       # Repo and tool discovery (list_repos, list_tools_for_repo)
  merge.py           # Content merging with pluggable strategies
  repo.py            # Git clone/cache helpers
  sources/           # Pluggable content source adapters
    __init__.py      # Source protocol + frontmatter parsing
    local.py         # Local directory source
    git.py           # Git repo source
tests/
  test_config.py
  test_discovery.py
  test_hierarchy.py
  test_merge.py
  test_server.py
  test_stdio.py              # End-to-end integration tests
  test_strategy_append.py
  test_strategy_merge_append.py
  test_strategy_template.py
  test_strategy_mixed.py
testing-helper-scripts/
  smoke.py                   # Smoke test client (stdio + HTTP)
examples/
  simple/                    # Overwrite strategy (default)
  append/                    # Append strategy
  merge-append/              # Merge-append strategy
  template/                  # Template strategy
docs/
  design.md                  # Architecture and design
  getting-started.md         # Quick start guide
  developer-guide.md         # This file
  merge-strategy-test-matrix.md  # Full test coverage matrix
```

## Running tests

```bash
make test              # all tests
make test-no-git       # skip git-based tests (avoids GPG key issues)
```

Tests are organized by layer:

| File | What it tests |
|------|--------------|
| `test_config.py` | YAML loading, includes, path resolution |
| `test_hierarchy.py` | Scope filtering, org prefix stripping |
| `test_merge.py` | Overwrite merging, provenance tracking |
| `test_discovery.py` | list_repos, list_tools_for_repo |
| `test_server.py` | MCP tool registration |
| `test_stdio.py` | End-to-end via stdio subprocess |
| `test_strategy_*.py` | Merge strategies (append, merge-append, template, mixed) |

## Linting

```bash
make lint              # check for issues
make lint-fix          # auto-fix
make format            # auto-format
```

Uses [ruff](https://docs.astral.sh/ruff/) for both linting and formatting.

## Running the server

```bash
make serve             # stdio (default)
make serve-http        # HTTP on localhost:8000
```

Both default to `./examples/simple/config.yml`. Override with:

```bash
make serve SDLC_MCP_CONFIG=./examples/merge-append/config.yml
```

## Calling tools manually

List all registered tools:

```bash
make list-tools
```

Call a tool without arguments:

```bash
make call TOOL=list_repos
```

Call a tool with arguments (JSON):

```bash
make call TOOL=list_tools_for_repo ARGS='{"repo":"api-gateway"}'
make call TOOL=testing ARGS='{"repo":"api-gateway"}'
```

Check version info:

```bash
make context-version
make context-version SDLC_MCP_CONFIG=./examples/merge-append/config.yml
```

Use `call-pretty` for formatted output (strips server logs, renders newlines):

```bash
make call-pretty TOOL=testing ARGS='{"repo":"api-gateway"}'
```

## Smoke tests

End-to-end tests that start the server and call discovery tools:

```bash
make smoke-stdio       # over stdio transport
make smoke-http        # over HTTP transport (starts/stops server)
```

## Adding a new merge strategy

1. Add the strategy name to `VALID_STRATEGIES` in `merge.py`
2. Add the merge logic in `merge_content()` — each strategy operates on the accumulated `ContentItem.content` from prior scopes
3. Write tests in a new `tests/test_strategy_<name>.py` file
4. Update `docs/merge-strategy-test-matrix.md` with test scenarios
5. Add an example under `examples/<name>/`
6. Update the strategy table in `README.md`, `CLAUDE.md`, and `docs/design.md`

## Adding a new content source

1. Create a new module under `src/sdlc_mcp/sources/` (follow `local.py` as a pattern)
2. Implement the `Source` protocol: a class with a `read() -> list[ContentItem]` method
3. Register it with `register_source("type_name", YourClass)` at module level
4. Import it in `server.py` to ensure registration (see the `_git`, `_local` imports)
5. Add tests

## Key design concepts

- **Scopes** are ordered. Config position determines merge order.
- **First scope** to provide a file is the base. Strategy only applies to subsequent scopes.
- **Strategy** is per-scope, not per-file (per-file via frontmatter is planned, see Phase 3.6 in design doc).
- **Merge-append** includes `scope specific overrides:` attribution labels.
- **Template** uses `@NAME` blocks as fillers and `{NAME}` placeholders with sigils for fill behavior.
- **Discovery tools** (`list_repos`, `list_tools_for_repo`, `context_version`) are built-in MCP tools, not content tools.
- **Content metadata** is an optional `context-metadata.yml` file alongside `config.yml` with flat key/value pairs, exposed via `context_version` prefixed with `context_`.
