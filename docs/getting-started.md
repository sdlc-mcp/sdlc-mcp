# Getting Started

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for package management

## Install

```bash
git clone <repo-url>
cd sdlc-mcp
make install
```

## Run the server

### stdio (default, for local use with Claude Code)

```bash
make serve
```

This uses the example config at `./examples/simple/config.yml` by default. To use a different config:

```bash
make serve SDLC_MCP_CONFIG=/path/to/your/config.yml
```

### HTTP (for remote/shared deployments)

```bash
make serve-http
```

Starts the server on `localhost:8000` using the streamable-http transport.

### Register with Claude Code

```bash
claude mcp add --transport stdio --scope project sdlc-mcp \
  -- uvx sdlc-mcp serve --config /path/to/config.yml
```

## Try it out

### List registered tools

```bash
make list-tools
```

### Call a specific tool

```bash
make call TOOL=list_repos
make call TOOL=list_tools_for_repo ARGS='{"repo":"api-gateway"}'
make call TOOL=testing ARGS='{"repo":"api-gateway"}'
```

### Check version info

```bash
make context-version
make context-version SDLC_MCP_CONFIG=./examples/merge-append/config.yml
```

### Smoke tests

Run the discovery tools end-to-end over stdio:

```bash
make smoke-stdio
```

Or over HTTP (starts a server, calls tools, shuts down):

```bash
make smoke-http
```

## Config

The server needs a config file to know what content to serve. If `--config` is not specified, it looks in:

1. `SDLC_MCP_CONFIG` environment variable
2. `/etc/sdlc-mcp/config.yml`
3. `~/.config/sdlc-mcp/config.yml`

The Makefile defaults `SDLC_MCP_CONFIG` to `./examples/simple/config.yml` for development.

## Content metadata

Place a `context-metadata.yml` file alongside your `config.yml` with flat key/value pairs:

```yaml
name: acme-engineering-standards
version: 2.1.0
```

The `context_version` tool reports this alongside the engine version and any wrapper packages. See the examples for reference.

## Examples

The `examples/` directory has four configs demonstrating each merge strategy:

| Directory | Strategy | What it shows |
|-----------|----------|---------------|
| `simple/` | overwrite (default) | Later scopes replace earlier ones |
| `append/` | append | Team content concatenated after org content |
| `merge-append/` | merge-append | Team content appended under matching markdown headings |
| `template/` | template | Org files declare `{PLACEHOLDER}` slots, teams fill with `@NAME` blocks |

Try any example:

```bash
make serve SDLC_MCP_CONFIG=./examples/merge-append/config.yml
make smoke-stdio SDLC_MCP_CONFIG=./examples/template/config.yml
```

## Next steps

- Read the [design doc](design.md) for architecture and strategy details
- See the [developer guide](developer-guide.md) for contributing
