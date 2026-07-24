# Create an sdlc-mcp Wrapper Package

This skill walks you through creating a wrapper package — a Python project that depends on `sdlc-mcp`, bundles your organization's config and content, and ships as its own MCP server.

## What you'll create

A standalone Python package that:
- Installs with `pip install your-org-mcp`
- Runs as `your-org-mcp serve`
- Delivers your org's engineering standards, code review guidelines, testing conventions, and other context to AI agents via MCP
- Gets auto-discovered by sdlc-mcp's `context_version` tool

## Step 1: Gather requirements

Before generating the project, ask the user:

1. **Project name** — What should the package be called? Convention is `<org>-mcp` or `<org>-sdlc-mcp` (e.g., `acme-mcp`). Must be lowercase with hyphens.
2. **Organization name** — Display name for the org (e.g., `Acme Corp`). Used in descriptions and content.
3. **Team names** — What teams need their own scoped content? (e.g., `api, frontend, data-layer`). Each team gets its own content directory and config scope.
4. **Default merge strategy** — How should team content combine with org content?
   - `overwrite` (default) — team content replaces org content for matching files
   - `append` — team content is concatenated after org content
   - `merge-append` — team content is appended under matching markdown headings

## Step 2: Generate the project

If you are in the sdlc-mcp repository, run:

```bash
make new-project NAME=<name> ORG="<org>" TEAMS="<teams>"
```

If you are NOT in the sdlc-mcp repo, generate the files directly following the structure in [docs/extending.md](https://github.com/shanemcd/sdlc-mcp/blob/main/docs/extending.md). The key files are:

- `pyproject.toml` with `dependencies = ["sdlc-mcp"]` and a `[project.scripts]` entry point
- `src/<package>/__main__.py` that imports `from sdlc_mcp.server import init_config_from_path, mcp`
- `config.yml` with org and team scopes
- `context-metadata.yml` with package name and version
- `content/org/*.md` with YAML frontmatter (`name`, `description`)
- `content/teams/<team>/*.md` for team-specific overrides
- `Makefile` with `install`, `serve`, `lint`, `list-tools` targets

## Step 3: Customize the generated project

Walk the user through:

### Config (`config.yml`)
- Add repo names to each team's `repos` list so content scopes correctly
- Optionally set `strategy: merge-append` on team scopes if layering is preferred over replacing
- Add `vars` to scopes for Jinja2 template values (e.g., `coverage_target: "90%"`)

### Content files
- Each `.md` file in `content/` becomes an MCP tool
- Frontmatter `name` is the tool name, `description` is what agents see
- Org-level files provide the baseline; team files override or extend for matching repos
- Common content types: `code-review.md`, `testing.md`, `security.md`, `deployment.md`, `architecture.md`

### Adding a new team
Add a scope to `config.yml` and create the team's content directory:
```yaml
- name: new-team
  repos: [repo-a, repo-b]
  sources:
    - type: local
      path: content/teams/new-team/
```

### Adding git-sourced content
Pull content from another repository:
```yaml
- name: shared-standards
  include:
    - git+https://github.com/org/standards.git
```

## Step 4: Test and register

```bash
cd <project-name>
make install
make serve          # verify it starts
make list-tools     # verify tools are registered
```

Register with Claude Code:
```bash
claude mcp add --transport stdio --scope project <project-name> \
  -- uvx <project-name> serve
```

## Reference

- [Extending sdlc-mcp](https://github.com/shanemcd/sdlc-mcp/blob/main/docs/extending.md) — full reference guide
- [sdlc-mcp README](https://github.com/shanemcd/sdlc-mcp) — hierarchy, merge strategies, vars
