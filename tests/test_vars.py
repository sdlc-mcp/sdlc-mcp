"""Tests for Jinja2 variable rendering in content."""

from sdlc_mcp.config import Config, Scope, SourceConfig
from sdlc_mcp.hierarchy import resolve_hierarchy
from sdlc_mcp.merge import merge_content
from sdlc_mcp.sources import local as _local  # noqa: F401


def _org_scope(tmp_path, files):
    org_dir = tmp_path / "org"
    org_dir.mkdir()
    for name, content in files.items():
        (org_dir / name).write_text(content)
    return Scope(name="platform", sources=[SourceConfig(type="local", path=str(org_dir))])


def test_basic_substitution(tmp_path):
    org = _org_scope(tmp_path, {"testing.md": "Coverage target: {{ coverage_target }}"})
    config = Config(
        scopes=[
            org,
            Scope(name="api", repos=["api-gw"], vars={"coverage_target": "90%"}),
        ]
    )
    hierarchy = resolve_hierarchy(config, "x/api-gw")
    merged = merge_content(hierarchy)
    assert "90%" in merged.get("testing.md").content


def test_multiple_vars(tmp_path):
    org = _org_scope(
        tmp_path,
        {
            "testing.md": "Target: {{ coverage_target }}\nFramework: {{ framework }}",
        },
    )
    config = Config(
        scopes=[
            org,
            Scope(
                name="api", repos=["api-gw"], vars={"coverage_target": "90%", "framework": "pytest"}
            ),
        ]
    )
    hierarchy = resolve_hierarchy(config, "x/api-gw")
    content = merge_content(hierarchy).get("testing.md").content
    assert "90%" in content
    assert "pytest" in content


def test_default_filter(tmp_path):
    org = _org_scope(
        tmp_path,
        {
            "testing.md": "Target: {{ coverage_target | default('80%') }}",
        },
    )
    config = Config(scopes=[org])
    hierarchy = resolve_hierarchy(config, "x/any-repo")
    assert "80%" in merge_content(hierarchy).get("testing.md").content


def test_default_overridden(tmp_path):
    org = _org_scope(
        tmp_path,
        {
            "testing.md": "Target: {{ coverage_target | default('80%') }}",
        },
    )
    config = Config(
        scopes=[
            org,
            Scope(name="api", repos=["api-gw"], vars={"coverage_target": "95%"}),
        ]
    )
    hierarchy = resolve_hierarchy(config, "x/api-gw")
    assert "95%" in merge_content(hierarchy).get("testing.md").content


def test_undefined_var_renders_empty(tmp_path):
    org = _org_scope(tmp_path, {"testing.md": "Target: {{ coverage_target }}"})
    config = Config(
        scopes=[
            org,
            Scope(name="api", repos=["api-gw"], vars={"other": "x"}),
        ]
    )
    hierarchy = resolve_hierarchy(config, "x/api-gw")
    content = merge_content(hierarchy).get("testing.md").content
    assert "Target:" in content
    assert "{{ coverage_target }}" not in content


def test_vars_apply_to_all_files(tmp_path):
    org = _org_scope(
        tmp_path,
        {
            "testing.md": "Target: {{ coverage_target }}",
            "review.md": "Team: {{ team_name }}",
        },
    )
    config = Config(
        scopes=[
            org,
            Scope(
                name="api", repos=["api-gw"], vars={"coverage_target": "90%", "team_name": "API"}
            ),
        ]
    )
    hierarchy = resolve_hierarchy(config, "x/api-gw")
    merged = merge_content(hierarchy)
    assert "90%" in merged.get("testing.md").content
    assert "API" in merged.get("review.md").content


def test_different_repos_get_different_vars(tmp_path):
    org = _org_scope(
        tmp_path,
        {
            "testing.md": "Target: {{ coverage_target | default('80%') }}",
        },
    )
    config = Config(
        scopes=[
            org,
            Scope(name="api", repos=["api-gw"], vars={"coverage_target": "90%"}),
            Scope(name="frontend", repos=["web-app"], vars={"coverage_target": "75%"}),
        ]
    )
    assert "90%" in merge_content(resolve_hierarchy(config, "x/api-gw")).get("testing.md").content
    assert "75%" in merge_content(resolve_hierarchy(config, "x/web-app")).get("testing.md").content


def test_non_matching_repo_no_vars(tmp_path):
    org = _org_scope(
        tmp_path,
        {
            "testing.md": "Target: {{ coverage_target | default('80%') }}",
        },
    )
    config = Config(
        scopes=[
            org,
            Scope(name="api", repos=["api-gw"], vars={"coverage_target": "90%"}),
        ]
    )
    content = merge_content(resolve_hierarchy(config, "x/other-repo")).get("testing.md").content
    assert "80%" in content


def test_vars_accumulate_across_scopes(tmp_path):
    org = _org_scope(
        tmp_path,
        {
            "testing.md": "Target: {{ coverage_target }}, Framework: {{ framework }}",
        },
    )
    config = Config(
        scopes=[
            org,
            Scope(name="division", vars={"coverage_target": "85%"}),
            Scope(name="api", repos=["api-gw"], vars={"framework": "pytest"}),
        ]
    )
    content = merge_content(resolve_hierarchy(config, "x/api-gw")).get("testing.md").content
    assert "85%" in content
    assert "pytest" in content


def test_later_vars_override_earlier(tmp_path):
    org = _org_scope(tmp_path, {"testing.md": "Target: {{ coverage_target }}"})
    config = Config(
        scopes=[
            org,
            Scope(name="division", vars={"coverage_target": "80%"}),
            Scope(name="api", repos=["api-gw"], vars={"coverage_target": "95%"}),
        ]
    )
    content = merge_content(resolve_hierarchy(config, "x/api-gw")).get("testing.md").content
    assert "95%" in content
    assert "80%" not in content


def test_jinja_conditional(tmp_path):
    org = _org_scope(
        tmp_path,
        {
            "testing.md": "{% if team_notes %}Notes: {{ team_notes }}{% endif %}",
        },
    )
    config = Config(
        scopes=[
            org,
            Scope(name="api", repos=["api-gw"], vars={"team_notes": "Use auth fixtures"}),
        ]
    )
    content = merge_content(resolve_hierarchy(config, "x/api-gw")).get("testing.md").content
    assert "Use auth fixtures" in content


def test_jinja_conditional_no_var(tmp_path):
    org = _org_scope(
        tmp_path,
        {
            "testing.md": "Base.{% if team_notes %}\nNotes: {{ team_notes }}{% endif %}",
        },
    )
    config = Config(
        scopes=[
            org,
            Scope(name="api", repos=["api-gw"], vars={"other": "x"}),
        ]
    )
    content = merge_content(resolve_hierarchy(config, "x/api-gw")).get("testing.md").content
    assert "Notes:" not in content


def test_vars_work_with_append_strategy(tmp_path):
    org = _org_scope(tmp_path, {"testing.md": "Org: {{ team_name }}"})
    team_dir = tmp_path / "team"
    team_dir.mkdir()
    (team_dir / "testing.md").write_text("Team additions for {{ team_name }}.")
    config = Config(
        scopes=[
            org,
            Scope(
                name="api",
                repos=["api-gw"],
                strategy="append",
                sources=[SourceConfig(type="local", path=str(team_dir))],
                vars={"team_name": "API"},
            ),
        ]
    )
    content = merge_content(resolve_hierarchy(config, "x/api-gw")).get("testing.md").content
    assert "Org: API" in content
    assert "Team additions for API" in content


def test_no_vars_leaves_content_unchanged(tmp_path):
    org = _org_scope(tmp_path, {"testing.md": "No templates here."})
    config = Config(scopes=[org])
    content = merge_content(resolve_hierarchy(config, "x/any-repo")).get("testing.md").content
    assert content == "No templates here."
