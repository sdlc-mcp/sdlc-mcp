"""Tests for mixed merge strategies across hierarchy levels.

Verifies that different scopes can use different strategies for the same file,
and that each strategy correctly operates on the accumulated result from prior
scopes.
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


def test_template_then_overwrite(tmp_path):
    """Overwrite wipes the filled template."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {TARGET}")
    _write_md(tmp_path / "div", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "team", "testing.md", "Team replaces everything.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="template",
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
    assert "85%" not in content
    assert "{TARGET}" not in content


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


def test_template_then_merge_append(tmp_path):
    """Filled template gets heading-level appends."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n{TEAM_SECTION}\n\n## Deploy\nOrg deploy.",
    )
    _write_md(
        tmp_path / "div",
        "testing.md",
        "@TEAM_SECTION\nDivision filled the template.",
    )
    _write_md(tmp_path / "team", "testing.md", "## Testing\nTeam merge-appended.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="template",
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

    assert "Division filled the template" in content
    assert "Team merge-appended" in content
    assert "Org deploy" in content
    assert "{TEAM_SECTION}" not in content


def test_template_then_append(tmp_path):
    """Filled template gets content concatenated."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {TARGET}")
    _write_md(tmp_path / "div", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "team", "testing.md", "Team appended at end.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="template",
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

    assert "85%" in content
    assert "Team appended at end" in content
    assert "{TARGET}" not in content


def test_append_then_template(tmp_path):
    """Template fills placeholders in appended result."""
    _write_md(tmp_path / "org", "testing.md", "Org testing.\n\n{TEAM_NOTES}")
    _write_md(tmp_path / "div", "testing.md", "Division appended.\n\n{TEAM_EXTRAS}")
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@TEAM_NOTES\nTeam notes.\n\n@TEAM_EXTRAS\nTeam extras.",
    )

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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org testing" in content
    assert "Division appended" in content
    assert "Team notes" in content
    assert "Team extras" in content
    assert "{TEAM_NOTES}" not in content
    assert "{TEAM_EXTRAS}" not in content


# ---- Multi-level mixed strategies ----


def test_three_levels_append_merge_append_overwrite(tmp_path):
    """append → merge-append → overwrite — overwrite at end wipes everything."""
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
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Team replaces everything" in content
    assert "Org testing" not in content
    assert "Division appended" not in content
    assert "Subdiv merge-appended" not in content


def test_three_levels_template_append_merge_append(tmp_path):
    """template → append → merge-append — each applies to accumulated result."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n{DIVISION_POLICY}\n\n## Deploy\nOrg deploy.",
    )
    _write_md(
        tmp_path / "div",
        "testing.md",
        "@DIVISION_POLICY\nDivision policy.",
    )
    _write_md(tmp_path / "subdiv", "testing.md", "Subdivision appended.")
    _write_md(tmp_path / "team", "testing.md", "## Deploy\nTeam deploy additions.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="division",
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "div"))],
            ),
            Scope(
                name="subdiv",
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "subdiv"))],
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

    assert "Division policy" in content
    assert "{DIVISION_POLICY}" not in content
    assert "Subdivision appended" in content
    assert "Org deploy" in content
    assert "Team deploy additions" in content


def test_five_scopes_mixed_strategies_with_repos(tmp_path):
    """Five scopes with mixed strategies and repo branching."""
    _write_md(tmp_path / "s0", "testing.md", "## Testing\nBase content.\n\n{TEAM_SECTION}")
    _write_md(tmp_path / "s1", "testing.md", "Scope 1 appended.")
    _write_md(tmp_path / "s2", "testing.md", "@TEAM_SECTION\nRepo A template fill.")
    _write_md(tmp_path / "s3", "testing.md", "## Testing\nRepo B merge-appended.")
    _write_md(tmp_path / "s4", "testing.md", "Repo A final append.")

    config = Config(
        scopes=[
            Scope(
                name="s0",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s0"))],
            ),
            Scope(
                name="s1",
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s1"))],
            ),
            Scope(
                name="s2",
                repos=["repo-a"],
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s2"))],
            ),
            Scope(
                name="s3",
                repos=["repo-b"],
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s3"))],
            ),
            Scope(
                name="s4",
                repos=["repo-a"],
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s4"))],
            ),
        ]
    )

    # Repo A: s0 (base) → s1 (append) → s2 (template) → s4 (append)
    hierarchy = resolve_hierarchy(config, "repo-a")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content
    assert "Base content" in content
    assert "Scope 1 appended" in content
    assert "Repo A template fill" in content
    assert "{TEAM_SECTION}" not in content
    assert "Repo A final append" in content
    assert "Repo B" not in content

    # Repo B: s0 (base) → s1 (append) → s3 (merge-append)
    hierarchy = resolve_hierarchy(config, "repo-b")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content
    assert "Base content" in content
    assert "Scope 1 appended" in content
    assert "Repo B merge-appended" in content
    assert "Repo A" not in content


# ---- Cross-cutting: General ----


def test_different_strategies_per_file(tmp_path):
    """Different files in same scope use different strategies (scope-level default)."""
    _write_md(tmp_path / "org", "testing.md", "Org testing.")
    _write_md(tmp_path / "org", "deploy.md", "## Deploy\nOrg deploy.")
    _write_md(tmp_path / "team", "testing.md", "Team replaces testing.")
    _write_md(tmp_path / "team", "deploy.md", "## Deploy\nTeam deploy additions.")

    # Both files use the scope's strategy — this tests that strategy applies
    # uniformly to all files in a scope
    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
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

    assert "Team replaces testing" in merged.get("testing.md").content
    assert "Org testing" not in merged.get("testing.md").content
    assert "Team deploy additions" in merged.get("deploy.md").content
    assert "Org deploy" not in merged.get("deploy.md").content


def test_no_strategy_defaults_to_overwrite(tmp_path):
    """No strategy specified — defaults to overwrite (backwards compatible)."""
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

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

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

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Team testing" in content
    assert "Org testing" not in content


def test_org_prefix_stripping_with_append(tmp_path):
    """Org prefix stripping works with non-overwrite strategies."""
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
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    for repo in ["acme/api-gateway", "somefork/api-gateway", "api-gateway"]:
        hierarchy = resolve_hierarchy(config, repo)
        merged = merge_content(hierarchy)
        content = merged.get("testing.md").content
        assert "Org testing" in content
        assert "Team testing" in content
