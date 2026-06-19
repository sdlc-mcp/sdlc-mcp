"""Tests for content merging."""

from sdlc_mcp.config import Config, Scope, SourceConfig
from sdlc_mcp.hierarchy import resolve_hierarchy
from sdlc_mcp.merge import merge_content, merge_content_for_category
from sdlc_mcp.sources import local as _local  # noqa: F401


def _make_config(tmp_path):
    company_dir = tmp_path / "company"
    company_dir.mkdir()
    (company_dir / "security.md").write_text("# Company Security\nCompany-level security.")
    (company_dir / "documentation.md").write_text("# Docs\nCompany docs format.")

    org_dir = tmp_path / "org"
    org_dir.mkdir()
    (org_dir / "testing.md").write_text("# Org Testing\nOrg-level testing.")
    (org_dir / "code-review.md").write_text("# Code Review\nOrg-level review.")

    team_dir = tmp_path / "team"
    team_dir.mkdir()
    (team_dir / "testing.md").write_text("# Team Testing\nTeam-level testing overrides org.")

    return Config(
        scopes=[
            Scope(
                name="acme",
                sources=[SourceConfig(type="local", path=str(company_dir))],
            ),
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(org_dir))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                sources=[SourceConfig(type="local", path=str(team_dir))],
            ),
        ]
    )


def test_most_specific_wins(tmp_path):
    config = _make_config(tmp_path)
    hierarchy = resolve_hierarchy(config, "acme/api-gateway")
    merged = merge_content(hierarchy)

    testing = merged.get("testing.md")
    assert testing is not None
    assert "Team-level testing" in testing.content
    assert "Org-level testing" not in testing.content


def test_unique_content_passes_through(tmp_path):
    config = _make_config(tmp_path)
    hierarchy = resolve_hierarchy(config, "acme/api-gateway")
    merged = merge_content(hierarchy)

    assert merged.get("security.md") is not None
    assert merged.get("code-review.md") is not None
    assert merged.get("documentation.md") is not None


def test_provenance_tracking(tmp_path):
    config = _make_config(tmp_path)
    hierarchy = resolve_hierarchy(config, "acme/api-gateway")
    merged = merge_content(hierarchy)

    assert merged.provenance["testing.md"] == "api:api"
    assert merged.provenance["security.md"] == "acme:acme"
    assert merged.provenance["code-review.md"] == "platform:platform"


def test_merge_content_for_category(tmp_path):
    config = _make_config(tmp_path)
    hierarchy = resolve_hierarchy(config, "acme/api-gateway")

    item = merge_content_for_category(hierarchy, "testing")
    assert item is not None
    assert "Team-level testing" in item.content

    item = merge_content_for_category(hierarchy, "security")
    assert item is not None
    assert "Company-level security" in item.content


def test_merge_content_for_missing_category(tmp_path):
    config = _make_config(tmp_path)
    hierarchy = resolve_hierarchy(config, "acme/api-gateway")

    item = merge_content_for_category(hierarchy, "nonexistent")
    assert item is None


def test_no_team_content_for_unknown_repo(tmp_path):
    config = _make_config(tmp_path)
    hierarchy = resolve_hierarchy(config, "acme/unknown-repo")
    merged = merge_content(hierarchy)

    assert merged.get("testing.md") is not None
    assert "Org-level testing" in merged.get("testing.md").content


def test_three_unscoped_scopes_last_wins(tmp_path):
    """Three unscoped scopes all have testing.md — last one wins."""
    company_dir = tmp_path / "company"
    company_dir.mkdir()
    (company_dir / "testing.md").write_text("# Testing\nCompany testing.")

    org_dir = tmp_path / "org"
    org_dir.mkdir()
    (org_dir / "testing.md").write_text("# Testing\nOrg testing.")

    division_dir = tmp_path / "division"
    division_dir.mkdir()
    (division_dir / "testing.md").write_text("# Testing\nDivision testing.")

    config = Config(
        scopes=[
            Scope(
                name="acme",
                sources=[SourceConfig(type="local", path=str(company_dir))],
            ),
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(org_dir))],
            ),
            Scope(
                name="division",
                sources=[SourceConfig(type="local", path=str(division_dir))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "any-repo")
    merged = merge_content(hierarchy)

    testing = merged.get("testing.md")
    assert testing is not None
    assert "Division testing" in testing.content
    assert "Org testing" not in testing.content
    assert "Company testing" not in testing.content
    assert merged.provenance["testing.md"] == "division:division"


def test_mixed_scoped_unscoped_ordering(tmp_path):
    """no repo -> no repo -> repo A -> repo B -> repo A.

    No repo call: gets 2nd scope (last unscoped).
    Repo A call: gets 5th scope (last matching).
    Repo B call: gets 4th scope (only match).
    """
    dirs = []
    for i in range(5):
        d = tmp_path / f"scope{i}"
        d.mkdir()
        (d / "testing.md").write_text(f"# Testing\nScope {i} testing.")
        dirs.append(d)

    config = Config(
        scopes=[
            Scope(
                name="scope0",
                sources=[SourceConfig(type="local", path=str(dirs[0]))],
            ),
            Scope(
                name="scope1",
                sources=[SourceConfig(type="local", path=str(dirs[1]))],
            ),
            Scope(
                name="scope2",
                repos=["repo-a"],
                sources=[SourceConfig(type="local", path=str(dirs[2]))],
            ),
            Scope(
                name="scope3",
                repos=["repo-b"],
                sources=[SourceConfig(type="local", path=str(dirs[3]))],
            ),
            Scope(
                name="scope4",
                repos=["repo-a"],
                sources=[SourceConfig(type="local", path=str(dirs[4]))],
            ),
        ]
    )

    # No repo: only unscoped match (scope0, scope1) — scope1 wins
    hierarchy = resolve_hierarchy(config, "")
    merged = merge_content(hierarchy)
    assert "Scope 1 testing" in merged.get("testing.md").content

    # Repo A: scope0, scope1 (unscoped), scope2, scope4 match — scope4 wins
    hierarchy = resolve_hierarchy(config, "repo-a")
    merged = merge_content(hierarchy)
    assert "Scope 4 testing" in merged.get("testing.md").content

    # Repo B: scope0, scope1 (unscoped), scope3 match — scope3 wins
    hierarchy = resolve_hierarchy(config, "repo-b")
    merged = merge_content(hierarchy)
    assert "Scope 3 testing" in merged.get("testing.md").content


def test_filenames_sorted(tmp_path):
    config = _make_config(tmp_path)
    hierarchy = resolve_hierarchy(config, "acme/api-gateway")
    merged = merge_content(hierarchy)

    filenames = merged.filenames()
    assert filenames == sorted(filenames)
