"""Content merging with pluggable strategies.

Strategies (configured per-scope, applied when the scope's content
merges into the accumulated result):

  overwrite     — full file replacement (default, backwards compatible)
  append        — concatenate after existing content
  merge-append  — append under matching markdown heading paths
  template      — fill {NAME} placeholders with @NAME blocks
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from .config import SourceConfig
from .hierarchy import ResolvedHierarchy
from .sources import ContentItem, get_source_class

logger = logging.getLogger(__name__)

VALID_STRATEGIES = {"overwrite", "append", "merge-append", "template"}


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


def _merge_nodes(existing: _MdNode, incoming: _MdNode) -> None:
    inc_body = incoming.body.strip()
    if inc_body:
        ext_body = existing.body.rstrip()
        if ext_body:
            existing.body = ext_body + "\n\n" + inc_body
        else:
            existing.body = inc_body

    for inc_child in incoming.children:
        match = _find_child(existing, inc_child.heading, inc_child.level)
        if match:
            _merge_nodes(match, inc_child)
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


def _merge_append_content(existing_text: str, incoming_text: str) -> str:
    existing_tree = _parse_md_tree(existing_text)
    incoming_tree = _parse_md_tree(incoming_text)
    _merge_nodes(existing_tree, incoming_tree)
    return _render_node(existing_tree)


# ---------------------------------------------------------------------------
# Template: @NAME blocks and {NAME} placeholders
# ---------------------------------------------------------------------------


def _parse_at_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("@") and len(line) > 1 and line[1:].strip():
            if current_name is not None:
                blocks[current_name] = "\n".join(current_lines).strip()
            current_name = line[1:].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        blocks[current_name] = "\n".join(current_lines).strip()

    return blocks


def _apply_template(
    existing: ContentItem,
    incoming_content: str,
    last_filler_values: dict[tuple[str, str], str],
) -> None:
    blocks = _parse_at_blocks(incoming_content)
    content = existing.content

    for name, value in blocks.items():
        if "{" + name + "}" in content:
            content = content.replace("{" + name + "}", value)
        elif "{?" + name + "}" in content:
            content = content.replace("{?" + name + "}", value)
        elif "{!" + name + "}" in content:
            last_filler_values[(existing.filename, name)] = value
        elif "{!?" + name + "}" in content:
            last_filler_values[(existing.filename, name)] = value

    existing.content = content


def _finalize_templates(
    merged: MergedContent, last_filler_values: dict[tuple[str, str], str]
) -> None:
    for item in merged.items.values():
        content = item.content

        for (filename, name), value in last_filler_values.items():
            if filename == item.filename:
                content = content.replace("{!" + name + "}", value)
                content = content.replace("{!?" + name + "}", value)

        content = re.sub(r"\{\?[A-Z0-9_]+\}", "", content)
        content = re.sub(r"\{!\?[A-Z0-9_]+\}", "", content)

        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")

        item.content = content.strip()


# ---------------------------------------------------------------------------
# Main merge
# ---------------------------------------------------------------------------


def merge_content(hierarchy: ResolvedHierarchy) -> MergedContent:
    """Merge content from all hierarchy levels using per-level strategies."""
    merged = MergedContent()
    last_filler_values: dict[tuple[str, str], str] = {}

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
                existing.content = _merge_append_content(existing.content, item.content)
                merged.provenance[item.filename] = f"{level.level}:{level.name}"
            elif strategy == "template":
                existing = merged.items[item.filename]
                _apply_template(existing, item.content, last_filler_values)
                merged.provenance[item.filename] = f"{level.level}:{level.name}"
            else:
                merged.items[item.filename] = item
                merged.provenance[item.filename] = f"{level.level}:{level.name}"

    _finalize_templates(merged, last_filler_values)

    return merged


def merge_content_for_category(hierarchy: ResolvedHierarchy, category: str) -> ContentItem | None:
    """Get a single content item by category (filename without .md extension)."""
    merged = merge_content(hierarchy)

    filename = category if category.endswith(".md") else f"{category}.md"
    return merged.get(filename)
