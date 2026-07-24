"""Tests for scripts/scaffold.py."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.scaffold import scaffold


def test_scaffold_creates_all_files(tmp_path: Path) -> None:
    project = scaffold("test-org-mcp", "Test Org", ["backend", "frontend"], tmp_path)

    assert project == tmp_path / "test-org-mcp"
    assert (project / "pyproject.toml").is_file()
    assert (project / "config.yml").is_file()
    assert (project / "context-metadata.yml").is_file()
    assert (project / "Makefile").is_file()
    assert (project / "README.md").is_file()
    assert (project / ".gitignore").is_file()
    assert (project / "src" / "test_org_mcp" / "__init__.py").is_file()
    assert (project / "src" / "test_org_mcp" / "__main__.py").is_file()
    assert (project / "content" / "org" / "code-review.md").is_file()
    assert (project / "content" / "org" / "testing.md").is_file()
    assert (project / "content" / "teams" / "backend" / "testing.md").is_file()
    assert (project / "content" / "teams" / "frontend" / "testing.md").is_file()


def test_scaffold_pyproject_has_sdlc_mcp_dependency(tmp_path: Path) -> None:
    scaffold("dep-test-mcp", "Dep Test", ["api"], tmp_path)

    content = (tmp_path / "dep-test-mcp" / "pyproject.toml").read_text()
    assert '"sdlc-mcp"' in content or "'sdlc-mcp'" in content


def test_scaffold_pyproject_has_entry_point(tmp_path: Path) -> None:
    scaffold("my-org-mcp", "My Org", ["api"], tmp_path)

    content = (tmp_path / "my-org-mcp" / "pyproject.toml").read_text()
    assert 'my-org-mcp = "my_org_mcp.__main__:main"' in content


def test_scaffold_config_is_valid_yaml(tmp_path: Path) -> None:
    scaffold("yaml-test-mcp", "Yaml Test", ["api", "frontend"], tmp_path)

    config_path = tmp_path / "yaml-test-mcp" / "config.yml"
    data = yaml.safe_load(config_path.read_text())

    assert isinstance(data, list)
    assert len(data) == 3

    assert data[0]["name"] == "yaml-test"
    assert data[0]["sources"][0]["type"] == "local"
    assert data[0]["sources"][0]["path"] == "content/org/"

    assert data[1]["name"] == "api"
    assert data[1]["repos"] == []

    assert data[2]["name"] == "frontend"


def test_scaffold_main_imports_sdlc_mcp(tmp_path: Path) -> None:
    scaffold("import-test-mcp", "Import Test", ["api"], tmp_path)

    content = (tmp_path / "import-test-mcp" / "src" / "import_test_mcp" / "__main__.py").read_text()
    assert "from sdlc_mcp.server import init_config_from_path, mcp" in content


def test_scaffold_content_has_frontmatter(tmp_path: Path) -> None:
    scaffold("fm-test-mcp", "FM Test", ["api"], tmp_path)

    content = (tmp_path / "fm-test-mcp" / "content" / "org" / "testing.md").read_text()
    assert content.startswith("---")
    assert "name: testing" in content
    assert "description:" in content


def test_scaffold_refuses_existing_directory(tmp_path: Path) -> None:
    (tmp_path / "existing-mcp").mkdir()

    import pytest

    with pytest.raises(SystemExit):
        scaffold("existing-mcp", "Existing", ["api"], tmp_path)


def test_scaffold_custom_teams(tmp_path: Path) -> None:
    scaffold("teams-mcp", "Teams", ["data-layer", "platform", "mobile"], tmp_path)

    project = tmp_path / "teams-mcp"
    assert (project / "content" / "teams" / "data-layer" / "testing.md").is_file()
    assert (project / "content" / "teams" / "platform" / "testing.md").is_file()
    assert (project / "content" / "teams" / "mobile" / "testing.md").is_file()

    config = yaml.safe_load((project / "config.yml").read_text())
    team_names = [s["name"] for s in config[1:]]
    assert team_names == ["data-layer", "platform", "mobile"]


def test_scaffold_org_name_in_content(tmp_path: Path) -> None:
    scaffold("acme-mcp", "Acme Corp", ["api"], tmp_path)

    content = (tmp_path / "acme-mcp" / "content" / "org" / "code-review.md").read_text()
    assert "Acme Corp" in content

    readme = (tmp_path / "acme-mcp" / "README.md").read_text()
    assert "Acme Corp" in readme
