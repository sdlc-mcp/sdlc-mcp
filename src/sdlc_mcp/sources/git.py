"""Git repository content source."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..repo import CACHE_DIR, cache_key, ensure_cloned
from . import ContentItem, register_source

if TYPE_CHECKING:
    from ..config import SourceConfig

logger = logging.getLogger(__name__)


class GitSource:
    def __init__(self, config: SourceConfig) -> None:
        self.url = config.url
        self.ref = config.ref
        self.subpath = config.path

    def read(self) -> list[ContentItem]:
        if not self.url:
            logger.warning("Git source has no URL configured")
            return []

        key = cache_key(self.url, self.ref)
        repo_dir = CACHE_DIR / key

        ensure_cloned(self.url, self.ref, repo_dir)

        if not repo_dir.exists():
            return []

        content_dir = repo_dir / self.subpath if self.subpath else repo_dir
        if not content_dir.is_dir():
            logger.warning("Path %s does not exist in cloned repo %s", self.subpath, self.url)
            return []

        items = []
        for md_file in sorted(content_dir.glob("*.md")):
            items.append(
                ContentItem.from_file(
                    filename=md_file.name,
                    raw_content=md_file.read_text(),
                    source_path=f"git:{self.url}:{self.subpath}/{md_file.name}",
                )
            )
        return items


register_source("git", GitSource)
