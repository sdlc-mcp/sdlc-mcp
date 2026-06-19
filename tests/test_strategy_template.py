"""Tests for the template merge strategy.

Template strategy: org file declares placeholder slots, incoming scopes fill them.

Placeholder sigils (in the base/org file):
  {FOO}   — first filler wins, left in output if unfilled
  {!FOO}  — last filler wins, left in output if unfilled
  {?FOO}  — first filler wins, stripped if unfilled
  {!?FOO} — last filler wins, stripped if unfilled

Filler syntax (in the incoming scope's file):
  @NAME starts a filler block. Content runs until the next @NAME or end of file.
  The NAME matches against the placeholder name (without sigil characters).
"""

from sdlc_mcp.config import Config, Scope, SourceConfig
from sdlc_mcp.hierarchy import resolve_hierarchy
from sdlc_mcp.merge import merge_content
from sdlc_mcp.sources import local as _local  # noqa: F401


# ---- Helpers ----


def _write_md(directory, filename, content):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(content)


# ---- Basic substitution ----


def test_single_placeholder_filled(tmp_path):
    """Single {FOO} placeholder replaced by team content."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n80% coverage.\n\n{TEAM_REQUIREMENTS}",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@TEAM_REQUIREMENTS\nContract tests required.",
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "80% coverage" in content
    assert "Contract tests required" in content
    assert "{TEAM_REQUIREMENTS}" not in content


def test_multiple_placeholders_all_filled(tmp_path):
    """Multiple placeholders, team fills all."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n{COVERAGE}\n\n## Deploy\n{DEPLOY_STEPS}",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@COVERAGE\n90% minimum.\n\n@DEPLOY_STEPS\nRun smoke tests first.",
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "90% minimum" in content
    assert "Run smoke tests first" in content
    assert "{COVERAGE}" not in content
    assert "{DEPLOY_STEPS}" not in content


def test_multiple_placeholders_some_filled(tmp_path):
    """Multiple placeholders, team fills some — unfilled left as-is."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n{COVERAGE}\n\n## Deploy\n{DEPLOY_STEPS}",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@COVERAGE\n90% minimum.",
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "90% minimum" in content
    assert "{DEPLOY_STEPS}" in content


def test_team_section_no_matching_placeholder(tmp_path):
    """Team provides section with no matching placeholder — ignored."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n80% coverage.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@NONEXISTENT\nThis has no placeholder.",
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "80% coverage" in content
    assert "This has no placeholder" not in content


def test_placeholder_mid_paragraph(tmp_path):
    """Placeholder in the middle of a paragraph — inline replacement."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "All teams must achieve {COVERAGE_TARGET} code coverage.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@COVERAGE_TARGET\n90%",
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "90%" in content
    assert "{COVERAGE_TARGET}" not in content
    assert "All teams must achieve" in content


def test_same_placeholder_appears_twice(tmp_path):
    """Same placeholder twice in org file — both replaced."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "Coverage: {TARGET}\n\nReminder: target is {TARGET}.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@TARGET\n90%",
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert content.count("90%") == 2
    assert "{TARGET}" not in content


def test_placeholder_vs_heading_no_collision(tmp_path):
    """Placeholder {COVERAGE} and heading ## COVERAGE don't collide."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## COVERAGE\nOrg coverage section.\n\nTarget: {COVERAGE_TARGET}",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@COVERAGE_TARGET\n90%",
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "## COVERAGE" in content
    assert "Org coverage section" in content
    assert "90%" in content
    assert "{COVERAGE_TARGET}" not in content


def test_file_only_in_scoped_scope_template(tmp_path):
    """File exists only in scoped scope with template strategy."""
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)

    assert merged.get("api-conventions.md") is not None
    assert "API conventions" in merged.get("api-conventions.md").content


def test_nested_placeholder_cascading(tmp_path):
    """Filled content contains a new placeholder — next scope resolves it."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n{TEAM_SECTION}",
    )
    _write_md(
        tmp_path / "div",
        "testing.md",
        "@TEAM_SECTION\nDivision rules.\n\n{TEAM_OVERRIDE}",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@TEAM_OVERRIDE\nTeam specific.",
    )

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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Division rules" in content
    assert "Team specific" in content
    assert "{TEAM_SECTION}" not in content
    assert "{TEAM_OVERRIDE}" not in content


def test_empty_section_for_placeholder(tmp_path):
    """Team provides empty section for placeholder — replaced with empty."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n{OPTIONAL_SECTION}\nEnd of doc.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@OPTIONAL_SECTION\n",
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "{OPTIONAL_SECTION}" not in content
    assert "End of doc" in content


# ---- N-level cascading ----


def test_division_fills_placeholder(tmp_path):
    """Org placeholder filled by division."""
    _write_md(tmp_path / "org", "testing.md", "## Testing\n{DIVISION_RULES}")
    _write_md(tmp_path / "div", "testing.md", "@DIVISION_RULES\nBackend rules.")

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
        ]
    )

    hierarchy = resolve_hierarchy(config, "")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Backend rules" in content
    assert "{DIVISION_RULES}" not in content


def test_division_skips_team_fills(tmp_path):
    """Division doesn't fill placeholder, team does."""
    _write_md(tmp_path / "org", "testing.md", "## Testing\n{TEAM_RULES}")
    _write_md(tmp_path / "div", "testing.md", "@OTHER\nDivision other stuff.")
    _write_md(tmp_path / "team", "testing.md", "@TEAM_RULES\nAPI team rules.")

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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "API team rules" in content
    assert "{TEAM_RULES}" not in content


def test_division_introduces_placeholder_team_fills(tmp_path):
    """Division's filled content introduces new placeholder, team fills it."""
    _write_md(tmp_path / "org", "testing.md", "## Testing\n{DIVISION_SECTION}")
    _write_md(
        tmp_path / "div",
        "testing.md",
        "@DIVISION_SECTION\nDivision content.\n\n{TEAM_EXTRAS}",
    )
    _write_md(tmp_path / "team", "testing.md", "@TEAM_EXTRAS\nTeam extras.")

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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Division content" in content
    assert "Team extras" in content
    assert "{DIVISION_SECTION}" not in content
    assert "{TEAM_EXTRAS}" not in content


def test_each_level_fills_different_placeholders(tmp_path):
    """Three placeholders, each filled by a different level."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "## Testing\n{COMPANY_POLICY}\n\n{DIVISION_RULES}\n\n{TEAM_CONVENTIONS}",
    )
    _write_md(tmp_path / "company", "testing.md", "@COMPANY_POLICY\nCompany policy.")
    _write_md(tmp_path / "div", "testing.md", "@DIVISION_RULES\nDivision rules.")
    _write_md(tmp_path / "team", "testing.md", "@TEAM_CONVENTIONS\nTeam conventions.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="company",
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "company"))],
            ),
            Scope(
                name="division",
                strategy="template",
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

    assert "Company policy" in content
    assert "Division rules" in content
    assert "Team conventions" in content
    assert "{COMPANY_POLICY}" not in content
    assert "{DIVISION_RULES}" not in content
    assert "{TEAM_CONVENTIONS}" not in content


# ---- Sigil: {FOO} first filler wins ----


def test_first_filler_wins_two_scopes(tmp_path):
    """{FOO} — first filler wins, second ignored."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {TARGET}")
    _write_md(tmp_path / "div", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "team", "testing.md", "@TARGET\n90%")

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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "85%" in content
    assert "90%" not in content


def test_first_filler_wins_three_scopes(tmp_path):
    """{FOO} — first filler wins across three scopes."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {TARGET}")
    _write_md(tmp_path / "s1", "testing.md", "@TARGET\n80%")
    _write_md(tmp_path / "s2", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "s3", "testing.md", "@TARGET\n90%")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="s1",
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s1"))],
            ),
            Scope(
                name="s2",
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s2"))],
            ),
            Scope(
                name="s3",
                repos=["api-gateway"],
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s3"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "80%" in content
    assert "85%" not in content
    assert "90%" not in content


def test_first_filler_unfilled_left_in_output(tmp_path):
    """{FOO} unfilled — left as literal text."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {TARGET}")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "{TARGET}" in content


# ---- Sigil: {!FOO} last filler wins ----


def test_last_filler_wins_two_scopes(tmp_path):
    """{!FOO} — last filler wins."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {!TARGET}")
    _write_md(tmp_path / "div", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "team", "testing.md", "@TARGET\n90%")

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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "90%" in content
    assert "85%" not in content


def test_last_filler_wins_three_scopes(tmp_path):
    """{!FOO} — last of three fillers wins."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {!TARGET}")
    _write_md(tmp_path / "s1", "testing.md", "@TARGET\n80%")
    _write_md(tmp_path / "s2", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "s3", "testing.md", "@TARGET\n90%")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="s1",
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s1"))],
            ),
            Scope(
                name="s2",
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s2"))],
            ),
            Scope(
                name="s3",
                repos=["api-gateway"],
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s3"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "90%" in content
    assert "80%" not in content
    assert "85%" not in content


def test_last_filler_only_middle_fills(tmp_path):
    """{!FOO} — only middle scope fills, its value stands."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {!TARGET}")
    _write_md(tmp_path / "div", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "team", "testing.md", "@OTHER\nUnrelated.")

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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "85%" in content


def test_last_filler_unfilled_left_in_output(tmp_path):
    """{!FOO} unfilled — left as literal text."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {!TARGET}")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "{!TARGET}" in content


# ---- Sigil: {?FOO} first filler, strip if empty ----


def test_optional_first_filler_two_scopes(tmp_path):
    """{?FOO} filled — first filler wins."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {?TARGET}")
    _write_md(tmp_path / "div", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "team", "testing.md", "@TARGET\n90%")

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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "85%" in content
    assert "90%" not in content


def test_optional_first_filler_three_scopes(tmp_path):
    """{?FOO} — first filler wins across three."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {?TARGET}")
    _write_md(tmp_path / "s1", "testing.md", "@TARGET\n80%")
    _write_md(tmp_path / "s2", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "s3", "testing.md", "@TARGET\n90%")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="s1",
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s1"))],
            ),
            Scope(
                name="s2",
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s2"))],
            ),
            Scope(
                name="s3",
                repos=["api-gateway"],
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s3"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "80%" in content


def test_optional_unfilled_stripped(tmp_path):
    """{?FOO} unfilled — stripped from output."""
    _write_md(tmp_path / "org", "testing.md", "Before.\n{?OPTIONAL}\nAfter.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "{?OPTIONAL}" not in content
    assert "Before." in content
    assert "After." in content


# ---- Sigil: {!?FOO} last filler, strip if empty ----


def test_override_optional_two_scopes(tmp_path):
    """{!?FOO} — last filler wins."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {!?TARGET}")
    _write_md(tmp_path / "div", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "team", "testing.md", "@TARGET\n90%")

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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "90%" in content
    assert "85%" not in content


def test_override_optional_three_scopes(tmp_path):
    """{!?FOO} — last of three fillers wins."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {!?TARGET}")
    _write_md(tmp_path / "s1", "testing.md", "@TARGET\n80%")
    _write_md(tmp_path / "s2", "testing.md", "@TARGET\n85%")
    _write_md(tmp_path / "s3", "testing.md", "@TARGET\n90%")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="s1",
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s1"))],
            ),
            Scope(
                name="s2",
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s2"))],
            ),
            Scope(
                name="s3",
                repos=["api-gateway"],
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s3"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "90%" in content


def test_override_optional_unfilled_stripped(tmp_path):
    """{!?FOO} unfilled — stripped from output."""
    _write_md(tmp_path / "org", "testing.md", "Before.\n{!?OPTIONAL}\nAfter.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "{!?OPTIONAL}" not in content
    assert "Before." in content
    assert "After." in content


# ---- Multi-branch with repos ----


def test_five_scopes_template_first_filler(tmp_path):
    """Five scopes with {FOO} — first filler per repo query."""
    _write_md(tmp_path / "s0", "testing.md", "Coverage: {TARGET}")
    _write_md(tmp_path / "s1", "testing.md", "@TARGET\nScope 1 value.")
    _write_md(tmp_path / "s2", "testing.md", "@TARGET\nScope 2 value.")
    _write_md(tmp_path / "s3", "testing.md", "@TARGET\nScope 3 value.")
    _write_md(tmp_path / "s4", "testing.md", "@TARGET\nScope 4 value.")

    config = Config(
        scopes=[
            Scope(
                name="s0",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s0"))],
            ),
            Scope(
                name="s1",
                strategy="template",
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s3"))],
            ),
            Scope(
                name="s4",
                repos=["repo-a"],
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s4"))],
            ),
        ]
    )

    # All queries: s1 is first filler (unscoped), wins for everyone
    for repo in ["repo-a", "repo-b", ""]:
        hierarchy = resolve_hierarchy(config, repo)
        merged = merge_content(hierarchy)
        content = merged.get("testing.md").content
        assert "Scope 1 value" in content


def test_five_scopes_template_last_filler(tmp_path):
    """Five scopes with {!FOO} — last filler per repo query."""
    _write_md(tmp_path / "s0", "testing.md", "Coverage: {!TARGET}")
    _write_md(tmp_path / "s1", "testing.md", "@TARGET\nScope 1 value.")
    _write_md(tmp_path / "s2", "testing.md", "@TARGET\nScope 2 value.")
    _write_md(tmp_path / "s3", "testing.md", "@TARGET\nScope 3 value.")
    _write_md(tmp_path / "s4", "testing.md", "@TARGET\nScope 4 value.")

    config = Config(
        scopes=[
            Scope(
                name="s0",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s0"))],
            ),
            Scope(
                name="s1",
                strategy="template",
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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s3"))],
            ),
            Scope(
                name="s4",
                repos=["repo-a"],
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "s4"))],
            ),
        ]
    )

    # Repo A: s0, s1, s2, s4 match — s4 is last filler
    hierarchy = resolve_hierarchy(config, "repo-a")
    merged = merge_content(hierarchy)
    assert "Scope 4 value" in merged.get("testing.md").content

    # Repo B: s0, s1, s3 match — s3 is last filler
    hierarchy = resolve_hierarchy(config, "repo-b")
    merged = merge_content(hierarchy)
    assert "Scope 3 value" in merged.get("testing.md").content

    # No repo: s0, s1 — s1 is last filler
    hierarchy = resolve_hierarchy(config, "")
    merged = merge_content(hierarchy)
    assert "Scope 1 value" in merged.get("testing.md").content


def test_different_repos_fill_same_placeholder_differently(tmp_path):
    """Different repos fill same {!FOO} with different values."""
    _write_md(tmp_path / "org", "testing.md", "Coverage: {!TARGET}")
    _write_md(tmp_path / "api", "testing.md", "@TARGET\n90% for APIs.")
    _write_md(tmp_path / "frontend", "testing.md", "@TARGET\n70% for frontend.")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "api"))],
            ),
            Scope(
                name="frontend",
                repos=["web-app"],
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "frontend"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    assert "90% for APIs" in merged.get("testing.md").content

    hierarchy = resolve_hierarchy(config, "web-app")
    merged = merge_content(hierarchy)
    assert "70% for frontend" in merged.get("testing.md").content


# ---- Mixed placeholders in one file ----


def test_mixed_first_and_last_filler_in_one_file(tmp_path):
    """{FOO} and {!BAR} in same file — independent behavior."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "First: {FIRST_WINS}\nLast: {!LAST_WINS}",
    )
    _write_md(
        tmp_path / "div",
        "testing.md",
        "@FIRST_WINS\nDiv first.\n\n@LAST_WINS\nDiv last.",
    )
    _write_md(
        tmp_path / "team",
        "testing.md",
        "@FIRST_WINS\nTeam first.\n\n@LAST_WINS\nTeam last.",
    )

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
                strategy="template",
                sources=[SourceConfig(type="local", path=str(tmp_path / "team"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "api-gateway")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "Div first" in content
    assert "Team first" not in content
    assert "Team last" in content
    assert "Div last" not in content


def test_mixed_optional_both_unfilled(tmp_path):
    """{?FOO} and {!?BAR} neither filled — both stripped."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "Before.\n{?OPT_FIRST}\nMiddle.\n{!?OPT_LAST}\nAfter.",
    )

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
            ),
        ]
    )

    hierarchy = resolve_hierarchy(config, "")
    merged = merge_content(hierarchy)
    content = merged.get("testing.md").content

    assert "{?OPT_FIRST}" not in content
    assert "{!?OPT_LAST}" not in content
    assert "Before." in content
    assert "Middle." in content
    assert "After." in content


def test_mixed_one_filled_one_stripped(tmp_path):
    """{FOO} filled, {?BAR} unfilled — FOO present, BAR stripped."""
    _write_md(
        tmp_path / "org",
        "testing.md",
        "Coverage: {TARGET}\nOptional: {?EXTRAS}",
    )
    _write_md(tmp_path / "team", "testing.md", "@TARGET\n90%")

    config = Config(
        scopes=[
            Scope(
                name="platform",
                sources=[SourceConfig(type="local", path=str(tmp_path / "org"))],
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

    assert "90%" in content
    assert "{?EXTRAS}" not in content
