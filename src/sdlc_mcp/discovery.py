"""Repo, tool, and version discovery.

Provides three discovery functions:
- list_repos: all unique repo names from config scopes
- list_tools_for_repo: per-tool provenance for a given repo
- get_version_info: engine version, wrapper packages, and content metadata
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from importlib.metadata import distributions, version
from pathlib import Path

import yaml

from .config import Config
from .hierarchy import resolve_hierarchy
from .merge import _read_sources

logger = logging.getLogger(__name__)


@dataclass
class ToolOverview:
    name: str
    description: str
    provided_by: str
    overrides: list[str] = field(default_factory=list)


def list_repos(config: Config) -> list[str]:
    """Return sorted unique repo names from all scopes' repos filters."""
    repos: set[str] = set()
    for scope in config.scopes:
        repos.update(scope.repos)
    return sorted(repos)


def list_tools_for_repo(config: Config, repo: str) -> list[ToolOverview]:
    """Return per-tool provenance info for a given repo.

    For each content file, reports which scope provides the winning version
    and which scopes were overridden (in hierarchy order, most general first).
    """
    hierarchy = resolve_hierarchy(config, repo)

    if not hierarchy.levels:
        return []

    # Track which scopes provided each filename, in hierarchy order
    filename_scopes: dict[str, list[str]] = {}
    # Track the winning item per filename (last write wins)
    winning_items: dict[str, tuple[str, str, str]] = {}  # filename -> (name, description, scope)

    for level in hierarchy.levels:
        items = _read_sources(level.sources)
        for item in items:
            if item.filename not in filename_scopes:
                filename_scopes[item.filename] = []
            filename_scopes[item.filename].append(level.name)
            winning_items[item.filename] = (
                item.tool_name,
                item.tool_description,
                level.name,
            )

    results: list[ToolOverview] = []
    for filename in sorted(winning_items):
        tool_name, description, provided_by = winning_items[filename]
        scopes = filename_scopes[filename]
        overrides = [s for s in scopes if s != provided_by]

        results.append(
            ToolOverview(
                name=tool_name,
                description=description,
                provided_by=provided_by,
                overrides=overrides,
            )
        )

    return results


def get_context_version(metadata_path: Path | None = None) -> dict[str, str]:
    """Return version info from all three layers.

    1. sdlc-mcp engine version (always)
    2. Wrapper packages that depend on sdlc-mcp (auto-discovered)
    3. Content metadata from context-metadata.yml (flat key/value, prefixed context_)
    """
    info: dict[str, str] = {}

    info["sdlc-mcp"] = version("sdlc-mcp")

    seen = set()
    for dist in distributions():
        name = dist.metadata["Name"]
        if name in seen or name == "sdlc-mcp":
            continue
        seen.add(name)
        requires = dist.requires or []
        if any("sdlc-mcp" in r for r in requires):
            info[name] = dist.version

    if metadata_path and metadata_path.exists():
        with open(metadata_path) as f:
            raw = yaml.safe_load(f)
        if isinstance(raw, dict):
            for key, value in raw.items():
                if isinstance(value, (str, int, float, bool)):
                    info[f"context_{key}"] = str(value)

    return info
