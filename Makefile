.PHONY: help install lint lint-fix format test test-no-git serve serve-http smoke-stdio smoke-http list-tools call

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
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
	uv run sdlc-mcp serve

serve-http: ## Run server via HTTP on localhost:8000
	uv run sdlc-mcp serve --transport streamable-http --host localhost --port 8000

smoke-stdio: ## Smoke test discovery tools over stdio transport
	uv run python testing-helper-scripts/smoke.py stdio

smoke-http: ## Smoke test discovery tools over HTTP transport
	@uv run sdlc-mcp serve --config examples/config.yml --transport streamable-http --host localhost --port 8000 & \
	PID=$$!; \
	sleep 2; \
	uv run python testing-helper-scripts/smoke.py http; \
	kill $$PID 2>/dev/null

list-tools: ## List all registered tools
	uv run fastmcp list tools -m sdlc_mcp --with-editable .

call: ## Call a tool (usage: make call TOOL=list_repos ARGS="")
	uv run fastmcp call -m sdlc_mcp --with-editable . $(TOOL) $(ARGS)
