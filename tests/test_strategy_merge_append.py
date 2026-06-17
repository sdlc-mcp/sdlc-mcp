"""Tests for the merge-append merge strategy.

Merge-append appends content under matching markdown heading paths.
Headings are matched hierarchically: ## > ### is a different key than
## Other > ###. Unmatched sections are appended at the end of the doc.
"""

from sdlc_mcp.config import Config, Scope, SourceConfig
from sdlc_mcp.hierarchy import resolve_hierarchy
from sdlc_mcp.merge import merge_content
from sdlc_mcp.sources import local as _local  # noqa: F401


# ---- Helpers ----


def _write_md(directory, filename, content):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(content)


# ---- Basic heading matching ----


def test_matching_h2_heading(tmp_path):
    """Content appended under matching ## heading."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n80% coverage.\n\n## Deploy\nUse CI pipeline.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## Testing\nContract tests required.",
    )

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "80% coverage" in content
    assert "Contract tests required" in content
    assert "Use CI pipeline" in content
    assert "api specific overrides:" in content
    # Attribution appears before the appended content
    assert content.index("api specific overrides:") < content.index("Contract tests required")
    # Contract tests should appear after 80% coverage (under same heading)
    assert content.index("80% coverage") < content.index("Contract tests required")
    # Deploy section untouched
    assert content.index("Contract tests required") < content.index("Use CI pipeline")


def test_matching_h3_under_same_h2(tmp_path):
    """Content appended under correct ## > ### path."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n\n### Coverage\n80% minimum.\n\n### Naming\nUse test_ prefix.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## Testing\n\n### Coverage\n90% for API surface.",
    )

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "80% minimum" in content
    assert "90% for API surface" in content
    assert "Use test_ prefix" in content
    assert "api specific overrides:" in content
    # 90% appended after 80% under ### Coverage
    assert content.index("80% minimum") < content.index("90% for API surface")
    # Naming section untouched
    assert "Use test_ prefix" in content


def test_same_h3_name_different_h2_parents(tmp_path):
    """### Coverage under ## Testing vs ## Deploy — only appends under correct parent."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n\n### Coverage\n80% minimum.\n\n## Deploy\n\n### Coverage\n100% for deploy.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## Testing\n\n### Coverage\n90% for API surface.",
    )

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    # 90% should appear after Testing > Coverage, not after Deploy > Coverage
    testing_coverage_idx = content.index("80% minimum")
    api_addition_idx = content.index("90% for API surface")
    deploy_coverage_idx = content.index("100% for deploy")

    assert testing_coverage_idx < api_addition_idx
    assert api_addition_idx < deploy_coverage_idx


def test_no_matching_heading_appended_at_end(tmp_path):
    """Team section with no matching heading appended at end of doc."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n80% coverage.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## API Conventions\nAll endpoints need contracts.",
    )

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "80% coverage" in content
    assert "API Conventions" in content
    assert "All endpoints need contracts" in content
    assert content.index("80% coverage") < content.index("API Conventions")


def test_body_text_under_h2_appended(tmp_path):
    """Body text under ## (no subsections) — team text appended after org text."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\nOrg testing guidelines.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## Testing\nTeam-specific additions.",
    )

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org testing guidelines" in content
    assert "Team-specific additions" in content
    assert "api specific overrides:" in content
    assert content.index("Org testing guidelines") < content.index("api specific overrides:")
    assert content.index("api specific overrides:") < content.index("Team-specific additions")


def test_h2_body_and_h3_children(tmp_path):
    """Team provides ## with body and ### children — both appended correctly."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\nOrg baseline.\n\n### Coverage\n80% minimum.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## Testing\nTeam note.\n\n### Coverage\n90% for APIs.",
    )

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org baseline" in content
    assert "Team note" in content
    assert "80% minimum" in content
    assert "90% for APIs" in content
    assert content.index("Org baseline") < content.index("Team note")
    assert content.index("80% minimum") < content.index("90% for APIs")


def test_only_h3_no_h2_body(tmp_path):
    """Team provides only ### content — ## body untouched."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\nOrg baseline.\n\n### Coverage\n80% minimum.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## Testing\n\n### Coverage\n90% for APIs.",
    )

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org baseline" in content
    assert "80% minimum" in content
    assert "90% for APIs" in content


# ---- Hierarchy depth ----


def test_h4_under_h3_under_h2(tmp_path):
    """Matches 3-deep heading path: ## > ### > ####."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n\n### Coverage\n\n#### Unit Tests\n80% minimum.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## Testing\n\n### Coverage\n\n#### Unit Tests\n90% for APIs.",
    )

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "80% minimum" in content
    assert "90% for APIs" in content
    assert content.index("80% minimum") < content.index("90% for APIs")


def test_team_adds_new_h4_under_existing_h3(tmp_path):
    """Team adds new #### under existing ###."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n\n### Coverage\n80% minimum.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## Testing\n\n### Coverage\n\n#### Integration Tests\nRequired for all APIs.",
    )

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "80% minimum" in content
    assert "#### Integration Tests" in content
    assert "Required for all APIs" in content


def test_new_h2_with_h3_children_appended_at_end(tmp_path):
    """Team adds entirely new ## with ### children — appended at end."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n80% coverage.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## API Standards\n\n### Versioning\nUse semver.\n\n### Auth\nOAuth2 required.",
    )

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "80% coverage" in content
    assert "## API Standards" in content
    assert "### Versioning" in content
    assert "### Auth" in content
    assert content.index("80% coverage") < content.index("API Standards")


# ---- N-level cascading ----


def test_three_scopes_append_to_same_h2(tmp_path):
    """Three scopes all merge-append to same ## — all bodies present in order with attribution."""
    _write_md(tmp_path / "company", "testing.md", "## Testing\nCompany baseline.")
    _write_md(tmp_path / "org", "testing.md", "## Testing\nOrg additions.")
    _write_md(tmp_path / "team", "testing.md", "## Testing\nTeam additions.")

    config = Config(
        scopes=[
            Scope(
                name="acme",
                sources=[SourceConfig(type="local", path=str(tmp_path / "company"))],
            ),
            Scope(
                name="platform",
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
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

    assert "Company baseline" in content
    assert "Org additions" in content
    assert "Team additions" in content
    assert "platform specific overrides:" in content
    assert "api specific overrides:" in content
    assert content.index("Company") < content.index("platform specific overrides:")
    assert content.index("platform specific overrides:") < content.index("Org additions")
    assert content.index("Org additions") < content.index("api specific overrides:")
    assert content.index("api specific overrides:") < content.index("Team additions")


def test_three_scopes_each_appends_to_different_h3(tmp_path):
    """Three scopes, each appends to a different ### — each gets only its append."""
    _write_md(
        tmp_path / "company",
        "testing.md",
        "## Testing\n\n### Coverage\nCompany coverage.\n\n### Naming\nCompany naming.\n\n### Tooling\nCompany tooling.",
    )
    _write_md(tmp_path / "org", "testing.md", "## Testing\n\n### Coverage\nOrg coverage update.")
    _write_md(tmp_path / "team", "testing.md", "## Testing\n\n### Naming\nTeam naming update.")

    config = Config(
        scopes=[
            Scope(
                name="acme",
                sources=[SourceConfig(type="local", path=str(tmp_path / "company"))],
            ),
            Scope(
                name="platform",
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
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

    assert "Company coverage" in content
    assert "Org coverage update" in content
    assert "Company naming" in content
    assert "Team naming update" in content
    assert "Company tooling" in content


def test_middle_scope_adds_h3_bottom_scope_appends_to_it(tmp_path):
    """Division adds new ###, team appends to it."""
    _write_md(tmp_path / "company", "testing.md", "## Testing\nCompany baseline.")
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n\n### API Contracts\nOrg API contract rules.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "## Testing\n\n### API Contracts\nTeam contract additions.",
    )

    config = Config(
        scopes=[
            Scope(
                name="acme",
                sources=[SourceConfig(type="local", path=str(tmp_path / "company"))],
            ),
            Scope(
                name="platform",
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
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

    assert "Company baseline" in content
    assert "Org API contract rules" in content
    assert "Team contract additions" in content
    assert content.index("Org API contract rules") < content.index("Team contract additions")


# ---- Multi-branch with repos ----


def test_five_scopes_merge_append_ordering(tmp_path):
    """Five scopes (2 unscoped, repo A, repo B, repo A), all merge-append.

    Repo A: 4 layers merged under headings.
    Repo B: 3 layers merged.
    No repo: 2 layers merged.
    """
    _write_md(tmp_path / "s0", "testing.md", "## Testing\nScope 0.")
    _write_md(tmp_path / "s1", "testing.md", "## Testing\nScope 1.")
    _write_md(tmp_path / "s2", "testing.md", "## Testing\nScope 2.")
    _write_md(tmp_path / "s3", "testing.md", "## Testing\nScope 3.")
    _write_md(tmp_path / "s4", "testing.md", "## Testing\nScope 4.")

    config = Config(
        scopes=[
            Scope(
                name="s0",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s0"))],
            ),
            Scope(
                name="s1",
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s1"))],
            ),
            Scope(
                name="s2",
                repos=["repo-a"],
                strategy="merge-append",
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
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s4"))],
            ),
        ]
    )

    # Repo A: s0, s1, s2, s4
    hierarchy = resolve_hierarchy(config, "repo-a")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content
    assert "Scope 0" in content
    assert "Scope 1" in content
    assert "Scope 2" in content
    assert "Scope 3" not in content
    assert "Scope 4" in content
    assert "s1 specific overrides:" in content
    assert "s2 specific overrides:" in content
    assert "s4 specific overrides:" in content

    # Repo B: s0, s1, s3
    hierarchy = resolve_hierarchy(config, "repo-b")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content
    assert "Scope 0" in content
    assert "Scope 1" in content
    assert "Scope 2" not in content
    assert "Scope 3" in content
    assert "Scope 4" not in content
    assert "s1 specific overrides:" in content
    assert "s3 specific overrides:" in content

    # No repo: s0, s1
    hierarchy = resolve_hierarchy(config, "")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content
    assert "Scope 0" in content
    assert "Scope 1" in content
    assert "Scope 2" not in content
    assert "s1 specific overrides:" in content


def test_different_repos_append_under_different_headings(tmp_path):
    """API team appends under ## Testing, frontend under ## Deploy."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\nOrg testing.\n\n## Deploy\nOrg deploy.",
    )
    _write_md(tmp_path / "api", "testing.md", "## Testing\nAPI testing additions.")
    _write_md(tmp_path / "frontend", "testing.md", "## Deploy\nFrontend deploy additions.")

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
                sources=[SourceConfig(type="local", path=str(tmp_path / "api"))],
            ),
            Scope(
                name="frontend",
                repos=["web-app"],
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "frontend"))],
            ),
        ]
    )

    # api-gateway: Testing gets API additions, Deploy untouched
    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content
    assert "API testing additions" in content
    assert "api specific overrides:" in content
    assert "Frontend deploy" not in content

    # web-app: Deploy gets frontend additions, Testing untouched
    hierarchy = resolve_hierarchy(config, "web-app")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content
    assert "Frontend deploy additions" in content
    assert "frontend specific overrides:" in content
    assert "API testing" not in content


def test_two_scoped_scopes_same_repo_different_h3(tmp_path):
    """Two scoped scopes for same repo, each appends under different ###."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n\n### Coverage\nOrg coverage.\n\n### Naming\nOrg naming.",
    )
    _write_md(tmp_path / "backend", "testing.md", "## Testing\n\n### Coverage\nBackend coverage.")
    _write_md(tmp_path / "api", "testing.md", "## Testing\n\n### Naming\nAPI naming.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="backend",
                repos=["api-gateway"],
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "backend"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="merge-append",
                sources=[SourceConfig(type="local", path=str(tmp_path / "api"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org coverage" in content
    assert "Backend coverage" in content
    assert "Org naming" in content
    assert "API naming" in content


# ---- Untouched content ----


def test_unmentioned_sections_untouched(tmp_path):
    """Org sections the team doesn't mention are untouched."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\nOrg testing.\n\n## Security\nOrg security.\n\n## Deploy\nOrg deploy.",
    )
    _write_md(tmp_path / "team", "testing.md", "## Testing\nTeam testing.")

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org security" in content
    assert "Org deploy" in content
    assert "Team testing" in content


def test_content_between_headings_preserved(tmp_path):
    """Non-heading paragraphs in org stay in place."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\nFirst paragraph.\n\nSecond paragraph.\n\n## Deploy\nDeploy content.",
    )
    _write_md(tmp_path / "team", "testing.md", "## Deploy\nTeam deploy note.")

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "First paragraph" in content
    assert "Second paragraph" in content
    assert content.index("First paragraph") < content.index("Second paragraph")


def test_frontmatter_preserved(tmp_path):
    """YAML frontmatter not affected by merge-append."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        '---\nname: testing\ndescription: "Testing"\n---\n## Testing\nOrg testing.',
    )
    _write_md(tmp_path / "team", "testing.md", "## Testing\nTeam testing.")

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    item = merged.get("testing.md")

    assert item.tool_name == "testing"
    assert "Org testing" in item.content
    assert "Team testing" in item.content


def test_disjoint_files_pass_through(tmp_path):
    """Different files across scopes pass through unchanged."""
    _write_md(tmp_path / "org", "testing.md", "## Testing\nOrg testing.")
    _write_md(tmp_path / "team", "deploy.md", "## Deploy\nTeam deploy.")

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)

    assert "Org testing" in merged.get("testing.md").content
    assert "Team deploy" in merged.get("deploy.md").content


# ---- Edge cases ----


def test_file_only_in_scoped_scope(tmp_path):
    """File exists only in scoped scope — merge-append to nothing."""
    _write_md(tmp_path / "org", "security.md", "Org security.")
    _write_md(tmp_path / "team", "api-conventions.md", "## Conventions\nAPI conventions.")

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)

    assert merged.get("api-conventions.md") is not None
    assert "API conventions" in merged.get("api-conventions.md").content


def test_empty_section_in_team_file(tmp_path):
    """Team has heading but no content under it — nothing appended."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\nOrg testing.",
    )
    _write_md(tmp_path / "team", "testing.md", "## Testing\n")

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org testing" in content


def test_team_heading_not_in_org_appended_at_end(tmp_path):
    """Team has heading org doesn't — appended at end."""
    _write_md(tmp_path / "org", "testing.md", "## Testing\nOrg testing.")
    _write_md(tmp_path / "team", "testing.md", "## Monitoring\nTeam monitoring.")

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
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Org testing" in content
    assert "## Monitoring" in content
    assert "Team monitoring" in content
    assert content.index("Org testing") < content.index("Monitoring")
