"""Tests for repo and tool discovery.

Tests for two new discovery functions:
- list_repos: returns sorted unique repo names from config scopes
- list_tools_for_repo: returns per-tool provenance info for a given repo,
  including which scope provides the winning version and which were overridden
"""

from sdlc_mcp.config import Config, Scope, SourceConfig
from sdlc_mcp.discovery import ToolOverview, list_repos, list_tools_for_repo
from sdlc_mcp.sources import local as _local  # noqa: F401

# ---- Helpers ----


def _make_standard_config(tmp_path):
    """3-level hierarchy: company (unscoped) -> org (unscoped) -> team (scoped).

    Content layout:
      company/  security.md, documentation.md
      org/      testing.md, code-review.md
      team/     testing.md  (overrides org)
    """
    company_dir = tmp_path / "company"
    company_dir.mkdir()
    (company_dir / "security.md").write_text(
        '---\nname: security\ndescription: "Security standards"\n---\n# Security\nCompany security.'
    )
    (company_dir / "documentation.md").write_text(
        '---\nname: documentation\ndescription: "Documentation format"\n---\n# Docs\nCompany docs.'
    )

    org_dir = tmp_path / "org"
    org_dir.mkdir()
    (org_dir / "testing.md").write_text(
        '---\nname: testing\ndescription: "Org testing strategy"\n---\n# Testing\nOrg testing.'
    )
    (org_dir / "code-review.md").write_text(
        '---\nname: code-review\ndescription: "Org code review"\n---\n# Code Review\nOrg review.'
    )

    team_dir = tmp_path / "team"
    team_dir.mkdir()
    (team_dir / "testing.md").write_text(
        '---\nname: testing\ndescription: "API testing conventions"\n---\n'
        "# API Testing\nTeam testing overrides org."
    )

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
                repos=["api-gateway", "api-auth"],
                sources=[SourceConfig(type="local", path=str(team_dir))],
            ),
        ]
    )


# ---- list_repos ----


def test_list_repos_empty_config():
    config = Config(scopes=[])
    assert list_repos(config) == []


def test_list_repos_org_only():
    """Scopes without repos filters contribute no repo names."""
    config = Config(
        scopes=[
            Scope(name="acme", sources=[SourceConfig(type="local", path="/x")]),
            Scope(name="platform", sources=[SourceConfig(type="local", path="/y")]),
        ]
    )
    assert list_repos(config) == []


def test_list_repos_single_scope():
    config = Config(
        scopes=[
            Scope(name="api", repos=["api-gateway", "api-auth"], sources=[]),
        ]
    )
    assert list_repos(config) == ["api-auth", "api-gateway"]


def test_list_repos_deduplicates():
    """Same repo in multiple scopes appears only once."""
    config = Config(
        scopes=[
            Scope(name="api", repos=["api-gateway"], sources=[]),
            Scope(name="team-b", repos=["api-gateway", "web-app"], sources=[]),
        ]
    )
    assert list_repos(config) == ["api-gateway", "web-app"]


def test_list_repos_multiple_distinct_scopes():
    config = Config(
        scopes=[
            Scope(name="api", repos=["api-gateway"], sources=[]),
            Scope(name="frontend", repos=["web-app", "design-system"], sources=[]),
        ]
    )
    assert list_repos(config) == ["api-gateway", "design-system", "web-app"]


def test_list_repos_mixed_scoped_and_unscoped():
    """Unscoped (org-wide) scopes don't contribute repo names."""
    config = Config(
        scopes=[
            Scope(
                name="acme",
                sources=[SourceConfig(type="local", path="/x")],
            ),
            Scope(name="api", repos=["api-gateway"], sources=[]),
            Scope(name="frontend", repos=["web-app"], sources=[]),
        ]
    )
    assert list_repos(config) == ["api-gateway", "web-app"]


def test_list_repos_sorted():
    """Results are sorted alphabetically."""
    config = Config(
        scopes=[
            Scope(name="z-team", repos=["zebra-service"], sources=[]),
            Scope(name="a-team", repos=["alpha-api"], sources=[]),
            Scope(name="m-team", repos=["mega-app"], sources=[]),
        ]
    )
    repos = list_repos(config)
    assert repos == ["alpha-api", "mega-app", "zebra-service"]
    assert repos == sorted(repos)


# ---- list_tools_for_repo ----


def test_tools_for_known_repo_with_override(tmp_path):
    """api-gateway matches 'api' scope, which overrides org-level testing.md."""
    config = _make_standard_config(tmp_path)
    tools = list_tools_for_repo(config, "api-gateway")

    by_name = {t.name: t for t in tools}

    # testing.md: exists at platform and api → api wins, platform overridden
    testing = by_name["testing"]
    assert testing.provided_by == "api"
    assert "platform" in testing.overrides

    # security.md: only at acme → no override
    security = by_name["security"]
    assert security.provided_by == "acme"
    assert security.overrides == []

    # code-review.md: only at platform → no override
    code_review = by_name["code-review"]
    assert code_review.provided_by == "platform"
    assert code_review.overrides == []

    # documentation.md: only at acme → no override
    documentation = by_name["documentation"]
    assert documentation.provided_by == "acme"
    assert documentation.overrides == []


def test_tools_for_unknown_repo_no_overrides(tmp_path):
    """Unknown repo gets only unscoped content. No overrides possible."""
    config = _make_standard_config(tmp_path)
    tools = list_tools_for_repo(config, "unknown-repo")

    by_name = {t.name: t for t in tools}

    assert "security" in by_name
    assert "testing" in by_name
    assert "code-review" in by_name
    assert "documentation" in by_name

    for tool in tools:
        assert tool.overrides == [], f"{tool.name} should have no overrides"


def test_tools_for_unknown_repo_uses_org_content(tmp_path):
    """Unknown repo sees org-level testing, not team-level."""
    config = _make_standard_config(tmp_path)
    tools = list_tools_for_repo(config, "unknown-repo")

    by_name = {t.name: t for t in tools}
    assert by_name["testing"].provided_by == "platform"


def test_tools_for_repo_org_prefix_stripped(tmp_path):
    """acme/api-gateway, somefork/api-gateway, and api-gateway all match."""
    config = _make_standard_config(tmp_path)

    tools_full = list_tools_for_repo(config, "acme/api-gateway")
    tools_fork = list_tools_for_repo(config, "somefork/api-gateway")
    tools_bare = list_tools_for_repo(config, "api-gateway")

    names_full = {t.name for t in tools_full}
    names_fork = {t.name for t in tools_fork}
    names_bare = {t.name for t in tools_bare}
    assert names_full == names_fork == names_bare

    for tools in [tools_full, tools_fork, tools_bare]:
        testing = next(t for t in tools if t.name == "testing")
        assert testing.provided_by == "api"
        assert "platform" in testing.overrides


def test_tools_for_empty_config():
    config = Config(scopes=[])
    tools = list_tools_for_repo(config, "any-repo")
    assert tools == []


def test_tools_for_repo_team_only_content(tmp_path):
    """Content exists only at team level with no org-level equivalent."""
    org_dir = tmp_path / "org"
    org_dir.mkdir()
    (org_dir / "testing.md").write_text(
        '---\nname: testing\ndescription: "Org testing"\n---\n# Testing\nOrg testing.'
    )

    team_dir = tmp_path / "team"
    team_dir.mkdir()
    (team_dir / "api-conventions.md").write_text(
        '---\nname: api-conventions\ndescription: "API conventions"\n---\n'
        "# API Conventions\nTeam-only content."
    )

    config = Config(
        scopes=[
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

    tools = list_tools_for_repo(config, "api-gateway")
    by_name = {t.name: t for t in tools}

    # api-conventions: team-only, no override
    api_conv = by_name["api-conventions"]
    assert api_conv.provided_by == "api"
    assert api_conv.overrides == []

    # testing: org-only for this repo (not overridden by team)
    testing = by_name["testing"]
    assert testing.provided_by == "platform"
    assert testing.overrides == []


def test_tools_for_repo_all_overridden(tmp_path):
    """Every org-level tool has a corresponding team override."""
    org_dir = tmp_path / "org"
    org_dir.mkdir()
    (org_dir / "testing.md").write_text("# Testing\nOrg testing.")
    (org_dir / "review.md").write_text("# Review\nOrg review.")

    team_dir = tmp_path / "team"
    team_dir.mkdir()
    (team_dir / "testing.md").write_text("# Testing\nTeam testing.")
    (team_dir / "review.md").write_text("# Review\nTeam review.")

    config = Config(
        scopes=[
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

    tools = list_tools_for_repo(config, "api-gateway")

    for tool in tools:
        assert tool.provided_by == "api"
        assert tool.overrides == ["platform"]


def test_tools_for_repo_descriptions_from_frontmatter(tmp_path):
    """Tool descriptions come from the winning version's frontmatter."""
    config = _make_standard_config(tmp_path)
    tools = list_tools_for_repo(config, "api-gateway")

    by_name = {t.name: t for t in tools}

    # testing.md was overridden by team → team's description wins
    assert by_name["testing"].description == "API testing conventions"

    # security.md is from company scope → company's description
    assert by_name["security"].description == "Security standards"


def test_tools_for_repo_multiple_repos_same_scope(tmp_path):
    """Both repos listed in the same scope get identical overrides."""
    config = _make_standard_config(tmp_path)

    gw_tools = list_tools_for_repo(config, "api-gateway")
    auth_tools = list_tools_for_repo(config, "api-auth")

    gw_map = {t.name: (t.provided_by, t.overrides) for t in gw_tools}
    auth_map = {t.name: (t.provided_by, t.overrides) for t in auth_tools}

    assert gw_map == auth_map


def test_tools_for_repo_different_teams_different_overrides(tmp_path):
    """Different team scopes override different tools."""
    org_dir = tmp_path / "org"
    org_dir.mkdir()
    (org_dir / "testing.md").write_text("# Testing\nOrg testing.")
    (org_dir / "deploy.md").write_text("# Deploy\nOrg deploy.")

    api_dir = tmp_path / "api"
    api_dir.mkdir()
    (api_dir / "testing.md").write_text("# Testing\nAPI testing.")

    fe_dir = tmp_path / "frontend"
    fe_dir.mkdir()
    (fe_dir / "deploy.md").write_text("# Deploy\nFrontend deploy.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(org_dir))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                sources=[SourceConfig(type="local", path=str(api_dir))],
            ),
            Scope(
                name="frontend",
                repos=["web-app"],
                sources=[SourceConfig(type="local", path=str(fe_dir))],
            ),
        ]
    )

    api_tools = list_tools_for_repo(config, "api-gateway")
    fe_tools = list_tools_for_repo(config, "web-app")

    api_by_name = {t.name: t for t in api_tools}
    fe_by_name = {t.name: t for t in fe_tools}

    # API team overrides testing, inherits deploy
    assert api_by_name["testing"].provided_by == "api"
    assert api_by_name["testing"].overrides == ["platform"]
    assert api_by_name["deploy"].provided_by == "platform"
    assert api_by_name["deploy"].overrides == []

    # Frontend team overrides deploy, inherits testing
    assert fe_by_name["deploy"].provided_by == "frontend"
    assert fe_by_name["deploy"].overrides == ["platform"]
    assert fe_by_name["testing"].provided_by == "platform"
    assert fe_by_name["testing"].overrides == []


def test_tools_for_repo_sorted_by_name(tmp_path):
    """Results are sorted alphabetically by tool name."""
    config = _make_standard_config(tmp_path)
    tools = list_tools_for_repo(config, "api-gateway")

    names = [t.name for t in tools]
    assert names == sorted(names)


def test_tools_for_repo_three_level_override(tmp_path):
    """Content overridden across 3 levels: company -> org -> team."""
    company_dir = tmp_path / "company"
    company_dir.mkdir()
    (company_dir / "testing.md").write_text("# Testing\nCompany testing.")

    org_dir = tmp_path / "org"
    org_dir.mkdir()
    (org_dir / "testing.md").write_text("# Testing\nOrg testing.")

    team_dir = tmp_path / "team"
    team_dir.mkdir()
    (team_dir / "testing.md").write_text("# Testing\nTeam testing.")

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
                name="api",
                repos=["api-gateway"],
                sources=[SourceConfig(type="local", path=str(team_dir))],
            ),
        ]
    )

    tools = list_tools_for_repo(config, "api-gateway")
    assert len(tools) == 1

    testing = tools[0]
    assert testing.name == "testing"
    assert testing.provided_by == "api"
    assert testing.overrides == ["acme", "platform"]


def test_tools_for_repo_no_repo_specified(tmp_path):
    """Empty string repo returns only unscoped content, no overrides."""
    config = _make_standard_config(tmp_path)
    tools = list_tools_for_repo(config, "")

    by_name = {t.name: t for t in tools}

    assert "security" in by_name
    assert "testing" in by_name
    assert "code-review" in by_name
    assert "documentation" in by_name

    for tool in tools:
        assert tool.overrides == []


def test_tools_for_repo_override_order_matches_hierarchy(tmp_path):
    """Overridden scopes are listed in hierarchy order (most general first)."""
    company_dir = tmp_path / "company"
    company_dir.mkdir()
    (company_dir / "testing.md").write_text("# Testing\nCompany.")

    org_dir = tmp_path / "org"
    org_dir.mkdir()
    (org_dir / "testing.md").write_text("# Testing\nOrg.")

    team_dir = tmp_path / "team"
    team_dir.mkdir()
    (team_dir / "testing.md").write_text("# Testing\nTeam.")

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
                name="api",
                repos=["api-gateway"],
                sources=[SourceConfig(type="local", path=str(team_dir))],
            ),
        ]
    )

    tools = list_tools_for_repo(config, "api-gateway")
    testing = tools[0]

    # overrides should be in hierarchy order: acme first (most general), then platform
    assert testing.overrides == ["acme", "platform"]


def test_tool_overview_fields():
    """ToolOverview has all expected fields."""
    overview = ToolOverview(
        name="testing",
        description="Testing conventions",
        provided_by="api",
        overrides=["platform"],
    )
    assert overview.name == "testing"
    assert overview.description == "Testing conventions"
    assert overview.provided_by == "api"
    assert overview.overrides == ["platform"]
