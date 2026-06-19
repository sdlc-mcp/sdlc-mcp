"""Tests for the append merge strategy.

Append concatenates content from later scopes after the base content.
No labels, no heading matching — just concatenation in scope order.
"""

from sdlc_mcp.config import Config, Scope, SourceConfig
from sdlc_mcp.hierarchy import resolve_hierarchy
from sdlc_mcp.merge import merge_content
from sdlc_mcp.sources import local as _local  # noqa: F401


# ---- Helpers ----


def _write_md(directory, filename, content):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(content)


# ---- Tests ----


def test_two_scopes_same_file_appended(tmp_path):
    """Second scope's content is appended after the first."""
    _write_md(tmp_path / "org", "testing.md", "# Testing\n80% coverage.")
    _write_md(tmp_path / "team", "testing.md", "Contract tests required.")

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

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)

    testing = merged.get("testing.md")
    assert testing is not None
    assert "80% coverage" in testing.content
    assert "Contract tests required" in testing.content
    assert testing.content.index("80% coverage") < testing.content.index("Contract tests required")


def test_three_scopes_same_file_all_appended(tmp_path):
    """Three scopes all append — content concatenated in scope order."""
    _write_md(tmp_path / "company", "testing.md", "Company testing baseline.")
    _write_md(tmp_path / "org", "testing.md", "Org testing additions.")
    _write_md(tmp_path / "team", "testing.md", "Team testing additions.")

    config = Config(
        scopes=[
            Scope(
                name="acme",
                sources=[SourceConfig(type="local", path=str(tmp_path / "company"))],
            ),
            Scope(
                name="platform",
                strategy="append",
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

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)

    testing = merged.get("testing.md")
    assert testing is not None
    content = testing.content
    assert "Company testing baseline" in content
    assert "Org testing additions" in content
    assert "Team testing additions" in content
    assert content.index("Company") < content.index("Org") < content.index("Team")


def test_disjoint_files_pass_through(tmp_path):
    """Different files across scopes — no collision, both pass through."""
    _write_md(tmp_path / "org", "testing.md", "# Testing\nOrg testing.")
    _write_md(tmp_path / "team", "deploy.md", "# Deploy\nTeam deploy.")

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

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)

    assert merged.get("testing.md") is not None
    assert "Org testing" in merged.get("testing.md").content
    assert merged.get("deploy.md") is not None
    assert "Team deploy" in merged.get("deploy.md").content


def test_mixed_shared_and_unique_files(tmp_path):
    """Shared files appended, unique files pass through unchanged."""
    _write_md(tmp_path / "org", "testing.md", "Org testing.")
    _write_md(tmp_path / "org", "security.md", "Org security.")
    _write_md(tmp_path / "team", "testing.md", "Team testing additions.")
    _write_md(tmp_path / "team", "api-conventions.md", "API conventions.")

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

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)

    # Shared file: appended
    testing = merged.get("testing.md")
    assert "Org testing" in testing.content
    assert "Team testing additions" in testing.content

    # Unique org file: unchanged
    assert "Org security" in merged.get("security.md").content

    # Unique team file: passed through
    assert "API conventions" in merged.get("api-conventions.md").content


def test_unknown_repo_only_unscoped_appended(tmp_path):
    """Unknown repo gets only unscoped content — scoped append doesn't apply."""
    _write_md(tmp_path / "org", "testing.md", "Org testing.")
    _write_md(tmp_path / "team", "testing.md", "Team testing additions.")

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

    hierarchy = resolve_hierarchy(config, "unknown-repo")
    merged = merge_content(hierarchy)

    testing = merged.get("testing.md")
    assert "Org testing" in testing.content
    assert "Team testing" not in testing.content


def test_multi_branch_different_repos_different_appends(tmp_path):
    """Different repos get different appended content."""
    _write_md(tmp_path / "org", "testing.md", "Org testing.")
    _write_md(tmp_path / "api", "testing.md", "API testing additions.")
    _write_md(tmp_path / "frontend", "testing.md", "Frontend testing additions.")

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
                sources=[SourceConfig(type="local", path=str(tmp_path / "api"))],
            ),
            Scope(
                name="frontend",
                repos=["web-app"],
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "frontend"))],
            ),
        ]
    )

    # api-gateway gets org + api
    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    testing = merged.get("testing.md")
    assert "Org testing" in testing.content
    assert "API testing additions" in testing.content
    assert "Frontend testing" not in testing.content

    # web-app gets org + frontend
    hierarchy = resolve_hierarchy(config, "web-app")
    merged = merge_content(hierarchy)
    testing = merged.get("testing.md")
    assert "Org testing" in testing.content
    assert "Frontend testing additions" in testing.content
    assert "API testing" not in testing.content


def test_file_only_in_scoped_scope_append(tmp_path):
    """File exists only in the scoped scope — append to nothing."""
    _write_md(tmp_path / "org", "security.md", "Org security.")
    _write_md(tmp_path / "team", "api-conventions.md", "API conventions.")

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

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)

    # File only in team scope — should still appear
    api_conv = merged.get("api-conventions.md")
    assert api_conv is not None
    assert "API conventions" in api_conv.content


def test_five_scopes_append_ordering(tmp_path):
    """Five scopes (2 unscoped, repo A, repo B, repo A), all append.

    Repo A: 4 layers (scope 0, 1, 2, 4)
    Repo B: 3 layers (scope 0, 1, 3)
    No repo: 2 layers (scope 0, 1)
    """
    for i in range(5):
        _write_md(tmp_path / f"scope{i}", "testing.md", f"Scope {i} content.")

    config = Config(
        scopes=[
            Scope(
                name="scope0",
                sources=[SourceConfig(type="local", path=str(tmp_path / "scope0"))],
            ),
            Scope(
                name="scope1",
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "scope1"))],
            ),
            Scope(
                name="scope2",
                repos=["repo-a"],
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "scope2"))],
            ),
            Scope(
                name="scope3",
                repos=["repo-b"],
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "scope3"))],
            ),
            Scope(
                name="scope4",
                repos=["repo-a"],
                strategy="append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "scope4"))],
            ),
        ]
    )

    # Repo A: scopes 0, 1, 2, 4
    hierarchy = resolve_hierarchy(config, "repo-a")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content
    assert "Scope 0" in content
    assert "Scope 1" in content
    assert "Scope 2" in content
    assert "Scope 3" not in content
    assert "Scope 4" in content
    assert content.index("Scope 0") < content.index("Scope 1")
    assert content.index("Scope 1") < content.index("Scope 2")
    assert content.index("Scope 2") < content.index("Scope 4")

    # Repo B: scopes 0, 1, 3
    hierarchy = resolve_hierarchy(config, "repo-b")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content
    assert "Scope 0" in content
    assert "Scope 1" in content
    assert "Scope 2" not in content
    assert "Scope 3" in content
    assert "Scope 4" not in content

    # No repo: scopes 0, 1
    hierarchy = resolve_hierarchy(config, "")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content
    assert "Scope 0" in content
    assert "Scope 1" in content
    assert "Scope 2" not in content
    assert "Scope 3" not in content
    assert "Scope 4" not in content
