"""Tests for the git content source adapter."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from sdlc_mcp.config import SourceConfig
from sdlc_mcp.repo import cache_key as _cache_key
from sdlc_mcp.sources import local as _local  # noqa: F401
from sdlc_mcp.sources.git import GitSource


def _create_bare_repo(tmp_path: Path, files: dict[str, str]) -> str:
    """Create a bare git repo with the given files and return its file:// URL."""
    work = tmp_path / "work"
    work.mkdir()

    subprocess.run(["git", "init", str(work)], capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=work, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=work, capture_output=True, check=True)

    for relpath, content in files.items():
        fpath = work / relpath
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content)

    subprocess.run(["git", "add", "."], cwd=work, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=work,
        capture_output=True,
        check=True,
    )

    bare = tmp_path / "bare.git"
    subprocess.run(
        ["git", "clone", "--bare", str(work), str(bare)],
        capture_output=True,
        check=True,
    )

    return f"file://{bare}"


def test_cache_key_deterministic():
    k1 = _cache_key("https://github.com/acme/standards.git", "main")
    k2 = _cache_key("https://github.com/acme/standards.git", "main")
    assert k1 == k2
    assert "standards" in k1


def test_cache_key_varies_by_ref():
    k1 = _cache_key("https://github.com/acme/standards.git", "main")
    k2 = _cache_key("https://github.com/acme/standards.git", "dev")
    assert k1 != k2


def test_clone_and_read(tmp_path):
    url = _create_bare_repo(
        tmp_path,
        {
            "docs/testing.md": "# Testing\nTest all the things.",
            "docs/security.md": "# Security\nBe secure.",
            "docs/README.txt": "Not markdown, should be ignored.",
        },
    )

    cache_dir = tmp_path / "cache"
    config = SourceConfig(type="git", url=url, path="docs")

    with patch("sdlc_mcp.sources.git.CACHE_DIR", cache_dir):
        source = GitSource(config)
        items = source.read()

    assert len(items) == 2
    filenames = {item.filename for item in items}
    assert filenames == {"security.md", "testing.md"}

    testing = next(i for i in items if i.filename == "testing.md")
    assert "Test all the things" in testing.content
    assert testing.source_path.startswith("git:")


def test_clone_root_path(tmp_path):
    url = _create_bare_repo(
        tmp_path,
        {"standards.md": "# Standards\nTop-level content."},
    )

    cache_dir = tmp_path / "cache"
    config = SourceConfig(type="git", url=url, path="")

    with patch("sdlc_mcp.sources.git.CACHE_DIR", cache_dir):
        source = GitSource(config)
        items = source.read()

    assert any(i.filename == "standards.md" for i in items)


def test_pull_on_second_read(tmp_path):
    url = _create_bare_repo(
        tmp_path,
        {"docs/v1.md": "# V1\nOriginal content."},
    )

    cache_dir = tmp_path / "cache"
    config = SourceConfig(type="git", url=url, path="docs")

    with patch("sdlc_mcp.sources.git.CACHE_DIR", cache_dir):
        source = GitSource(config)
        items1 = source.read()
        assert len(items1) == 1

        items2 = source.read()
        assert len(items2) == 1


def test_missing_subpath(tmp_path):
    url = _create_bare_repo(
        tmp_path,
        {"root.md": "# Root"},
    )

    cache_dir = tmp_path / "cache"
    config = SourceConfig(type="git", url=url, path="nonexistent/path")

    with patch("sdlc_mcp.sources.git.CACHE_DIR", cache_dir):
        source = GitSource(config)
        items = source.read()

    assert items == []


def test_no_url():
    config = SourceConfig(type="git", url="", path="docs")
    source = GitSource(config)
    items = source.read()
    assert items == []


def test_integration_with_merge(tmp_path):
    """Test that git sources work through the full merge pipeline."""
    from sdlc_mcp.config import Config, Scope, SourceConfig
    from sdlc_mcp.hierarchy import resolve_hierarchy
    from sdlc_mcp.merge import merge_content

    url = _create_bare_repo(
        tmp_path,
        {
            "company/security.md": "# Git Security\nFrom git repo.",
            "company/docs.md": "# Git Docs\nFrom git repo.",
        },
    )

    local_dir = tmp_path / "local"
    local_dir.mkdir()
    (local_dir / "security.md").write_text("# Local Security\nTeam override.")

    cache_dir = tmp_path / "cache"

    config = Config(
        scopes=[
            Scope(
                name="acme",
                sources=[SourceConfig(type="git", url=url, path="company")],
            ),
            Scope(
                name="api",
                repos=["api-gateway"],
                sources=[SourceConfig(type="local", path=str(local_dir))],
            ),
        ]
    )

    with patch("sdlc_mcp.sources.git.CACHE_DIR", cache_dir):
        hierarchy = resolve_hierarchy(config, "acme/api-gateway")
        merged = merge_content(hierarchy)

    assert "Local Security" in merged.get("security.md").content
    assert "Git Docs" in merged.get("docs.md").content
    assert merged.provenance["security.md"] == "api:api"
    assert merged.provenance["docs.md"] == "acme:acme"
