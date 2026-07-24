"""FastMCP server with MCP tool definitions."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml
from fastmcp import FastMCP
from fastmcp.tools import Tool

from .config import Config, load_config
from .discovery import (
    get_context_version as _get_context_version,
)
from .discovery import (
    list_repos as _list_repos,
)
from .discovery import (
    list_tools_for_repo as _list_tools_for_repo,
)
from .hierarchy import resolve_hierarchy
from .merge import merge_content, merge_content_for_category

# Ensure source adapters are registered
from .sources import git as _git  # noqa: F401

logger = logging.getLogger(__name__)


def _build_auth():
    """Build a GoogleProvider auth backend if credentials are configured."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        return None

    from fastmcp.server.auth.providers.google import GoogleProvider

    base_url = os.environ.get("SDLC_MCP_BASE_URL", "http://localhost:8000")
    logger.info("Google OAuth enabled (client_id=%s…)", client_id[:8])
    return GoogleProvider(
        client_id=client_id,
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        base_url=base_url,
    )


mcp = FastMCP("sdlc-mcp", auth=_build_auth())

_config: Config | None = None
_metadata_path: Path | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def init_config(config: Config) -> None:
    global _config
    _config = config


def init_config_from_path(
    config_paths: list[Path] | None = None,
    repo_path: Path | None = None,
) -> None:
    global _config, _metadata_path
    _config = load_config(repo_path=repo_path, config_paths=config_paths)
    if config_paths:
        _metadata_path = config_paths[0].parent / "context-metadata.yml"
    register_content_tools()
    register_discovery_tools()
    total = sum(1 for k in mcp.local_provider._components if k.startswith("tool:"))
    logger.info("Registered %d tools total", total)


def _scope_has_category(scope, category: str) -> bool:
    filename = f"{category}.md"
    for source in scope.sources:
        if source.type == "local" and source.path:
            path = Path(source.path)
            if path.is_dir() and (path / filename).exists():
                return True
            if path.is_file() and path.name == filename:
                return True
    return False


def _make_content_tool(category: str, description: str):
    """Create a tool function that returns content for a specific category."""

    def tool_fn(repo: str | None = None) -> str:
        config = get_config()

        hierarchy = resolve_hierarchy(config, repo or "")
        item = merge_content_for_category(hierarchy, category)

        if item is None:
            available = []
            for s in config.scopes:
                if s.repos and _scope_has_category(s, category):
                    available.append(f"{s.name} (repos: {', '.join(s.repos)})")
            if available:
                return (
                    f"No matching content for {category!r}. Available for: {'; '.join(available)}"
                )
            return f"No content found for {category!r}"

        return item.content

    tool_fn.__name__ = f"{category.replace('-', '_')}"
    tool_fn.__qualname__ = tool_fn.__name__
    return tool_fn


def _make_context_version_tool():
    """Create a tool function that returns version info."""

    def tool_fn() -> str:
        info = _get_context_version(metadata_path=_metadata_path)
        return "\n".join(f"{k}: {v}" for k, v in info.items())

    tool_fn.__name__ = "context_version"
    tool_fn.__qualname__ = tool_fn.__name__
    return tool_fn


def _make_list_repos_tool():
    """Create a tool function that lists all configured repos."""

    def tool_fn() -> str:
        config = get_config()
        repos = _list_repos(config)
        if not repos:
            return "No repo-specific scopes configured."
        return "\n".join(repos)

    tool_fn.__name__ = "list_repos"
    tool_fn.__qualname__ = tool_fn.__name__
    return tool_fn


def _make_list_tools_for_repo_tool():
    """Create a tool function that lists tools available for a given repo."""

    def tool_fn(repo: str) -> str:
        config = get_config()
        tools = _list_tools_for_repo(config, repo)
        if not tools:
            return f"No tools found for repo {repo!r}."
        lines = []
        for t in tools:
            if t.overrides:
                lines.append(
                    f"{t.name}: {t.description} (provided by: {t.provided_by}, overrides: {', '.join(t.overrides)})"
                )
            else:
                lines.append(f"{t.name}: {t.description} (provided by: {t.provided_by})")
        return "\n".join(lines)

    tool_fn.__name__ = "list_tools_for_repo"
    tool_fn.__qualname__ = tool_fn.__name__
    return tool_fn


def register_content_tools() -> None:
    """Scan all content sources and register a tool per artifact."""
    config = get_config()

    if not config.scopes:
        return

    first_repo = ""
    for scope in config.scopes:
        if scope.repos:
            first_repo = scope.repos[0]
            break

    hierarchy = resolve_hierarchy(config, first_repo)
    merged = merge_content(hierarchy)

    for filename in merged.filenames():
        item = merged.items[filename]
        category = filename.removesuffix(".md")
        tool_name = f"{category.replace('-', '_')}"

        description = item.tool_description
        if not description:
            first_line = item.content.strip().split("\n", 1)[0].lstrip("# ").strip()
            description = first_line

        fn = _make_content_tool(category, description)
        tool = Tool.from_function(fn, name=tool_name, description=description)
        mcp.add_tool(tool)

    logger.info("Registered %d content tools", len(merged.items))


def _make_list_skills_tool():
    """Create a tool function that lists available skills from the registry."""

    def tool_fn() -> str:
        registry_path = Path(__file__).resolve().parent.parent.parent / "skills" / "registry.yml"
        if not registry_path.exists():
            return "No skills registry found."
        with open(registry_path) as f:
            data = yaml.safe_load(f)
        if not data or "skills" not in data:
            return "No skills registered."
        lines = []
        for skill in data["skills"]:
            lines.append(
                f"{skill['name']}: {skill['description']} [{skill.get('category', 'general')}]"
            )
        return "\n".join(lines)

    tool_fn.__name__ = "list_skills"
    tool_fn.__qualname__ = tool_fn.__name__
    return tool_fn


def register_discovery_tools() -> None:
    fn = _make_list_repos_tool()
    tool = Tool.from_function(
        fn,
        name="list_repos",
        description="List all repos that have repo-specific content configured",
    )
    mcp.add_tool(tool)
    logger.info("Registered list_repos discovery tool")

    fn = _make_list_tools_for_repo_tool()
    tool = Tool.from_function(
        fn,
        name="list_tools_for_repo",
        description="List available tools for a repo, showing which scope provides each and any overrides",
    )
    mcp.add_tool(tool)
    logger.info("Registered list_tools_for_repo discovery tool")

    fn = _make_context_version_tool()
    tool = Tool.from_function(
        fn,
        name="context_version",
        description="Version info for the sdlc-mcp engine, wrapper packages, and content metadata",
    )
    mcp.add_tool(tool)
    logger.info("Registered context_version discovery tool")

    fn = _make_list_skills_tool()
    tool = Tool.from_function(
        fn,
        name="list_skills",
        description="List available skills for working with sdlc-mcp (scaffolding, content authoring, troubleshooting)",
    )
    mcp.add_tool(tool)
    logger.info("Registered list_skills discovery tool")
