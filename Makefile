SDLC_MCP_CONFIG ?= ./examples/simple/config.yml

.PHONY: help install install-dependencies lint lint-fix format test test-no-git serve serve-http smoke-stdio smoke-http list-tools call call-pretty context-version new-project install-skill list-skills

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'

install: install-dependencies ## Install SDLC-MCP locally
	uv pip install -e .
	@uv run python -c "from importlib.metadata import version; print('sdlc-mcp:', version('sdlc-mcp'))"

install-dependencies: ## Install/Update dependencies
	uv sync

lint: ## Run linter and format check
	uvx ruff check .
	uvx ruff format --check .

lint-fix: ## Auto-fix lint issues
	uvx ruff check --fix .

format: ## Auto-format code
	uvx ruff format .

test: ## Run all tests
	uv run --with pytest pytest

test-no-git: ## Run tests, skipping git-based tests
	uv run --with pytest pytest --ignore=tests/test_git_source.py

serve: ## Run server via stdio (default)
	SDLC_MCP_CONFIG=$(SDLC_MCP_CONFIG) uv run sdlc-mcp serve

serve-http: ## Run server via HTTP on localhost:8000
	SDLC_MCP_CONFIG=$(SDLC_MCP_CONFIG) uv run sdlc-mcp serve --transport streamable-http --host localhost --port 8000

smoke-stdio: ## Smoke test discovery tools over stdio transport
	uv run python testing-helper-scripts/smoke.py stdio

smoke-http: ## Smoke test discovery tools over HTTP transport
	@SDLC_MCP_CONFIG=$(SDLC_MCP_CONFIG) uv run sdlc-mcp serve --transport streamable-http --host localhost --port 8000 & \
	PID=$$!; \
	sleep 2; \
	uv run python testing-helper-scripts/smoke.py http; \
	kill $$PID 2>/dev/null

list-tools: ## List all registered tools
	uv run fastmcp list --command "uv run sdlc-mcp serve --config $(SDLC_MCP_CONFIG)"

call: ## Call a tool (usage: make call TOOL=list_repos ARGS='{"repo":"api-gateway"}')
	uv run fastmcp call --command "uv run sdlc-mcp serve --config $(SDLC_MCP_CONFIG)" --target $(TOOL) $(if $(ARGS),--input-json '$(ARGS)')

call-pretty: ## Call a tool with formatted output (same args as call)
	@uv run fastmcp call --command "uv run sdlc-mcp serve --config $(SDLC_MCP_CONFIG)" --target $(TOOL) $(if $(ARGS),--input-json '$(ARGS)') --json 2>/dev/null | python3 -c "import sys,json; print(json.loads(sys.stdin.read())['content'][0]['text'])"

context-version: ## Show context version info
	@make call-pretty TOOL=context_version

new-project: ## Scaffold a wrapper package (usage: make new-project NAME=my-org-mcp)
ifndef NAME
	$(error NAME is required. Usage: make new-project NAME=my-org-mcp [ORG="Acme Corp"] [TEAMS="api,frontend"])
endif
	uv run python scripts/scaffold.py --name $(NAME) $(if $(ORG),--org "$(ORG)") $(if $(TEAMS),--teams "$(TEAMS)")
	@echo ""
	@echo "Next steps:"
	@echo "  cd $(NAME)"
	@echo "  make install"
	@echo "  make serve"

install-skill: ## Install a skill (usage: make install-skill SKILL=extend-sdlc-mcp)
ifndef SKILL
	$(error SKILL is required. Usage: make install-skill SKILL=extend-sdlc-mcp)
endif
	@mkdir -p .claude/skills
	@cp skills/$(SKILL).md .claude/skills/$(SKILL).md
	@echo "Installed skill '$(SKILL)' to .claude/skills/$(SKILL).md"

list-skills: ## List available skills from the registry
	@uv run python -c "import yaml; data=yaml.safe_load(open('skills/registry.yml')); [print(f\"  {s['name']:30s} {s['description']}\") for s in data['skills']]"
