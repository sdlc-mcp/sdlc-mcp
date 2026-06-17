"""Hierarchy resolution engine.

Filters config scopes to those applicable to a given repo,
preserving the order from the config (which defines the merge order).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .config import Config, SourceConfig

logger = logging.getLogger(__name__)


@dataclass
class HierarchyLevel:
    level: str
    name: str
    sources: list[SourceConfig] = field(default_factory=list)
    strategy: str = "overwrite"


@dataclass
class ResolvedHierarchy:
    repo: str
    levels: list[HierarchyLevel] = field(default_factory=list)

    def get_level(self, name: str) -> HierarchyLevel | None:
        for level in self.levels:
            if level.name == name:
                return level
        return None


def resolve_hierarchy(config: Config, repo: str) -> ResolvedHierarchy:
    """Resolve which scopes apply to a given repo.

    Returns scopes in config order. Scopes without a repos filter apply
    to all repos. Scopes with a repos filter apply only when the repo
    name matches.
    """
    resolved = ResolvedHierarchy(repo=repo)

    for scope in config.scopes_for_repo(repo):
        if scope.sources:
            resolved.levels.append(
                HierarchyLevel(
                    level=scope.name,
                    name=scope.name,
                    sources=list(scope.sources),
                    strategy=scope.strategy,
                )
            )

    return resolved
