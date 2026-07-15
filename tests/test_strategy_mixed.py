"""Tests for mixed merge strategies across hierarchy levels.

Verifies that different scopes can use different strategies for the same file,
and that each strategy correctly operates on the accumulated result from prior
scopes. Also tests that vars rendering works alongside all strategies.
"""

from sdlc_mcp.config import Config, Scope, SourceConfig
from sdlc_mcp.hierarchy import resolve_hierarchy
from sdlc_mcp.merge import merge_content
from sdlc_mcp.sources import local as _local  # noqa: F401


# ---- Helpers ----


def _write_md(directory, filename, content):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(content)


# ---- Pairwise strategy transitions ----


def test_append_then_overwrite(tmp_path):
    """Overwrite wipes the appended result."""
    _write_md(tmp_path / "org", "testing.md", "Org testing.")
    _write_md(tmp_path / "div", "testing.md", "Division additions.")
    _write_md(tmp_path / "team", "testing.md", "Team replaces everything.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "div"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="overwrite",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Team replaces everything" in content
    assert "Org testing" not in content
    assert "Division additions" not in content


def test_merge_append_then_overwrite(tmp_path):
    """Overwrite wipes the merge-appended result."""
    _write_md(tmp_path / "org", "testing.md", "## Testing\nOrg testing.")
    _write_md(tmp_path / "div", "testing.md", "## Testing\nDivision additions.")
    _write_md(tmp_path / "team", "testing.md", "Team replaces everything.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "div"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="overwrite",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Team replaces everything" in content
    assert "Org testing" not in content
    assert "Division additions" not in content


def test_overwrite_then_append(tmp_path):
    """Append adds to the overwritten version."""
    _write_md(tmp_path / "org", "testing.md", "Org testing.")
    _write_md(tmp_path / "div", "testing.md", "Division replaces org.")
    _write_md(tmp_path / "team", "testing.md", "Team appends to division.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="overwrite",
                sources=[SourceConfig(type="local", path=str(tmp_path / "div"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org testing" not in content
    assert "Division replaces org" in content
    assert "Team appends to division" in content
    assert content.index("Division replaces org") < content.index("Team appends to division")


def test_overwrite_then_merge_append(tmp_path):
    """Merge-append into the overwritten version."""
    _write_md(tmp_path / "org", "testing.md", "## Testing\nOrg testing.")
    _write_md(tmp_path / "div", "testing.md", "## Testing\nDivision replaces org.")
    _write_md(tmp_path / "team", "testing.md", "## Testing\nTeam merges into division.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="overwrite",
                sources=[SourceConfig(type="local", path=str(tmp_path / "div"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org testing" not in content
    assert "Division replaces org" in content
    assert "Team merges into division" in content


def test_append_then_merge_append(tmp_path):
    """Merge-append into the appended result."""
    _write_md(tmp_path / "org", "testing.md", "## Testing\nOrg testing.")
    _write_md(tmp_path / "div", "testing.md", "Division appended.")
    _write_md(tmp_path / "team", "testing.md", "## Testing\nTeam merge-appended.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "div"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org testing" in content
    assert "Division appended" in content
    assert "Team merge-appended" in content


def test_merge_append_then_append(tmp_path):
    """Append after the merge-appended result."""
    _write_md(tmp_path / "org", "testing.md", "## Testing\nOrg testing.")
    _write_md(tmp_path / "div", "testing.md", "## Testing\nDivision merge-appended.")
    _write_md(tmp_path / "team", "testing.md", "Team appended at end.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "div"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org testing" in content
    assert "Division merge-appended" in content
    assert "Team appended at end" in content


def test_vars_with_append(tmp_path):
    """Vars render after append merging."""
    _write_md(tmp_path / "org", "testing.md", "Org: {{ team_name }}")
    _write_md(tmp_path / "team", "testing.md", "Team: {{ team_name }}")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
                vars={"team_name": "API"},
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    content = merge_content(hierarchy).get("testing.md").content

    assert "Org: API" in content
    assert "Team: API" in content


def test_vars_with_merge_append(tmp_path):
    """Vars render after merge-append merging."""
    _write_md(tmp_path / "org", "testing.md", "## Testing\n{{ team_name }} org rules.")
    _write_md(tmp_path / "team", "testing.md", "## Testing\n{{ team_name }} team rules.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
                vars={"team_name": "API"},
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    content = merge_content(hierarchy).get("testing.md").content

    assert "API org rules" in content
    assert "API team rules" in content


# ---- Multi-level ----


def test_three_levels_append_merge_append_overwrite(tmp_path):
    """append -> merge-append -> overwrite: overwrite at end wipes everything."""
    _write_md(tmp_path / "org", "testing.md", "Org testing.")
    _write_md(tmp_path / "div", "testing.md", "Division appended.")
    _write_md(tmp_path / "subdiv", "testing.md", "## Testing\nSubdiv merge-appended.")
    _write_md(tmp_path / "team", "testing.md", "Team replaces everything.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "div"))],
            ),
            Scope(
                name="subdiv",
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "subdiv"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="overwrite",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    content = merge_content(hierarchy).get("testing.md").content

    assert "Team replaces everything" in content
    assert "Org testing" not in content


# ---- Cross-cutting ----


def test_no_strategy_defaults_to_overwrite(tmp_path):
    """No strategy specified defaults to overwrite."""
    _write_md(tmp_path / "org", "testing.md", "Org testing.")
    _write_md(tmp_path / "team", "testing.md", "Team testing.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    content = merge_content(resolve_hierarchy(config, "api-gateway")).get("testing.md").content
    assert "Team testing" in content
    assert "Org testing" not in content


def test_invalid_strategy_falls_back_to_overwrite(tmp_path):
    """Invalid strategy value falls back to overwrite."""
    _write_md(tmp_path / "org", "testing.md", "Org testing.")
    _write_md(tmp_path / "team", "testing.md", "Team testing.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="invalid-strategy",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    content = merge_content(resolve_hierarchy(config, "api-gateway")).get("testing.md").content
    assert "Team testing" in content
    assert "Org testing" not in content
