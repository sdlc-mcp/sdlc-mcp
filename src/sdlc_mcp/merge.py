"""Content merging with pluggable strategies.

Strategies control how files with the same name combine when multiple
scopes provide them:

  overwrite     -- full file replacement (default, backwards compatible)
  append        -- concatenate after existing content
  merge-append  -- append under matching markdown heading paths

Separately, scopes can declare vars which are rendered into content
via Jinja2 after merge resolution. Vars accumulate through the
hierarchy (later scopes override earlier ones for the same key).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import jinja2

from .config import SourceConfig
from .hierarchy import ResolvedHierarchy
from .sources import ContentItem, get_source_class

logger = logging.getLogger(__name__)

VALID_STRATEGIES = {"overwrite", "append", "merge-append"}


@dataclass
class MergedContent:
    items: dict[str, ContentItem] = field(default_factory=dict)
    provenance: dict[str, str] = field(default_factory=dict)

    def get(self, filename: str) -> ContentItem | None:
        return self.items.get(filename)

    def filenames(self) -> list[str]:
        return sorted(self.items.keys())


def _read_sources(sources: list[SourceConfig]) -> list[ContentItem]:
    items = []
    for source_config in sources:
        try:
            source_cls = get_source_class(source_config.type)
        except ValueError:
            logger.warning("Skipping unknown source type: %s", source_config.type)
            continue

        source = source_cls(source_config)
        items.extend(source.read())
    return items


# ---------------------------------------------------------------------------
# Merge-append: markdown heading tree
# ---------------------------------------------------------------------------


@dataclass
class _MdNode:
    level: int
    heading: str
    body: str
    children: list[_MdNode] = field(default_factory=list)


def _parse_md_tree(text: str) -> _MdNode:
    root = _MdNode(level=0, heading="", body="", children=[])
    stack: list[_MdNode] = [root]
    body_lines: list[str] = []

    for line in text.split("\n"):
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            stack[-1].body = "\n".join(body_lines)
            body_lines = []

            level = len(m.group(1))
            heading = m.group(2).strip()
            node = _MdNode(level=level, heading=heading, body="")

            while len(stack) > 1 and stack[-1].level >= level:
                stack.pop()

            stack[-1].children.append(node)
            stack.append(node)
        else:
            body_lines.append(line)

    stack[-1].body = "\n".join(body_lines)
    return root


def _find_child(parent: _MdNode, heading: str, level: int) -> _MdNode | None:
    for child in parent.children:
        if child.heading == heading and child.level == level:
            return child
    return None


def _merge_nodes(existing: _MdNode, incoming: _MdNode, scope_name: str = "") -> None:
    inc_body = incoming.body.strip()
    if inc_body:
        ext_body = existing.body.rstrip()
        labeled = f"{scope_name} specific overrides:\n{inc_body}" if scope_name else inc_body
        if ext_body:
            existing.body = ext_body + "\n\n" + labeled
        else:
            existing.body = labeled

    for inc_child in incoming.children:
        match = _find_child(existing, inc_child.heading, inc_child.level)
        if match:
            _merge_nodes(match, inc_child, scope_name)
        else:
            existing.children.append(inc_child)


def _render_node(node: _MdNode) -> str:
    parts: list[str] = []
    if node.heading:
        parts.append("#" * node.level + " " + node.heading)
    body = node.body.strip()
    if body:
        parts.append(body)
    for child in node.children:
        parts.append(_render_node(child))
    return "\n\n".join(p for p in parts if p)


def _merge_append_content(existing_text: str, incoming_text: str, scope_name: str = "") -> str:
    existing_tree = _parse_md_tree(existing_text)
    incoming_tree = _parse_md_tree(incoming_text)
    _merge_nodes(existing_tree, incoming_tree, scope_name)
    return _render_node(existing_tree)


# ---------------------------------------------------------------------------
# Jinja2 variable rendering
# ---------------------------------------------------------------------------


def _render_vars(content: str, vars: dict[str, str]) -> str:
    env = jinja2.Environment(undefined=jinja2.Undefined, keep_trailing_newline=True)
    template = env.from_string(content)
    rendered = template.render(**vars)
    while "\n\n\n" in rendered:
        rendered = rendered.replace("\n\n\n", "\n\n")
    return rendered.strip()


# ---------------------------------------------------------------------------
# Main merge
# ---------------------------------------------------------------------------


def merge_content(hierarchy: ResolvedHierarchy) -> MergedContent:
    """Merge content from all hierarchy levels, then render vars."""
    merged = MergedContent()
    accumulated_vars: dict[str, str] = {}

    for level in hierarchy.levels:
        items = _read_sources(level.sources)
        strategy = level.strategy if level.strategy in VALID_STRATEGIES else "overwrite"

        for item in items:
            if item.filename not in merged.items:
                merged.items[item.filename] = item
                merged.provenance[item.filename] = f"{level.level}:{level.name}"
            elif strategy == "append":
                existing = merged.items[item.filename]
                existing.content = existing.content.rstrip() + "\n\n" + item.content
                merged.provenance[item.filename] = f"{level.level}:{level.name}"
            elif strategy == "merge-append":
                existing = merged.items[item.filename]
                existing.content = _merge_append_content(existing.content, item.content, level.name)
                merged.provenance[item.filename] = f"{level.level}:{level.name}"
            else:
                merged.items[item.filename] = item
                merged.provenance[item.filename] = f"{level.level}:{level.name}"

        if level.vars:
            accumulated_vars.update(level.vars)

    if accumulated_vars:
        for item in merged.items.values():
            item.content = _render_vars(item.content, accumulated_vars)

    return merged


def merge_content_for_category(hierarchy: ResolvedHierarchy, category: str) -> ContentItem | None:
    """Get a single content item by category (filename without .md extension)."""
    merged = merge_content(hierarchy)

    filename = category if category.endswith(".md") else f"{category}.md"
    return merged.get(filename)
