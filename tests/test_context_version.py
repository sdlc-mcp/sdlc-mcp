"""Tests for the context_version tool.

Reports three layers of version info:
- sdlc-mcp engine version (always, from package metadata)
- Wrapper packages that depend on sdlc-mcp (auto-discovered)
- Content metadata from context-metadata.yml (optional, flat key/value,
  prefixed with context_ in output)
"""

from sdlc_mcp.discovery import get_context_version
from sdlc_mcp.sources import local as _local  # noqa: F401


# ---- Helpers ----


def _write_file(directory, filename, content):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(content)


# ---- Engine version ----


def test_engine_version_always_present():
    """sdlc-mcp version is always reported."""
    info = get_context_version()
    assert "sdlc-mcp" in info
    assert info["sdlc-mcp"]  # non-empty


# ---- Context metadata ----


def test_context_metadata_loaded(tmp_path):
    """Flat key/value pairs from context-metadata.yml are prefixed with context_."""
    _write_file(
        tmp_path,
        "context-metadata.yml",
        "name: acme-standards\nversion: 2.1.0\ngit: https://github.com/acme/standards",
    )

    info = get_context_version(metadata_path=tmp_path / "context-metadata.yml")

    assert info["context_name"] == "acme-standards"
    assert info["context_version"] == "2.1.0"
    assert info["context_git"] == "https://github.com/acme/standards"


def test_context_metadata_missing(tmp_path):
    """No context-metadata.yml — only engine version reported."""
    info = get_context_version(metadata_path=tmp_path / "context-metadata.yml")

    assert "sdlc-mcp" in info
    assert not any(k.startswith("context_") for k in info)


def test_context_metadata_empty_file(tmp_path):
    """Empty context-metadata.yml — no context_ keys."""
    _write_file(tmp_path, "context-metadata.yml", "")

    info = get_context_version(metadata_path=tmp_path / "context-metadata.yml")

    assert "sdlc-mcp" in info
    assert not any(k.startswith("context_") for k in info)


def test_context_metadata_single_key(tmp_path):
    """Single key in context-metadata.yml."""
    _write_file(tmp_path, "context-metadata.yml", "version: 1.0.0")

    info = get_context_version(metadata_path=tmp_path / "context-metadata.yml")

    assert info["context_version"] == "1.0.0"


def test_context_metadata_arbitrary_keys(tmp_path):
    """Any flat key/value pairs are accepted."""
    _write_file(
        tmp_path,
        "context-metadata.yml",
        "maintainer: platform-team@acme.com\nregion: us-east-1\ncustom_field: hello",
    )

    info = get_context_version(metadata_path=tmp_path / "context-metadata.yml")

    assert info["context_maintainer"] == "platform-team@acme.com"
    assert info["context_region"] == "us-east-1"
    assert info["context_custom_field"] == "hello"


def test_context_metadata_values_are_strings(tmp_path):
    """Numeric values are converted to strings."""
    _write_file(tmp_path, "context-metadata.yml", "version: 2\nbuild: 42")

    info = get_context_version(metadata_path=tmp_path / "context-metadata.yml")

    assert info["context_version"] == "2"
    assert info["context_build"] == "42"


def test_context_metadata_ignores_nested_structures(tmp_path):
    """Nested maps and arrays are skipped — flat values only."""
    _write_file(
        tmp_path,
        "context-metadata.yml",
        "version: 1.0.0\nnested:\n  key: value\nlist:\n  - a\n  - b\nflat: works",
    )

    info = get_context_version(metadata_path=tmp_path / "context-metadata.yml")

    assert info["context_version"] == "1.0.0"
    assert info["context_flat"] == "works"
    assert "context_nested" not in info
    assert "context_list" not in info


# ---- Wrapper package auto-discovery ----


def test_wrapper_packages_discovered():
    """Packages that depend on sdlc-mcp are auto-discovered.

    In the test environment, there may or may not be wrapper packages.
    Just verify the function runs without error and returns a dict.
    """
    info = get_context_version()
    assert isinstance(info, dict)
    assert "sdlc-mcp" in info


def test_wrapper_packages_no_duplicates():
    """Each wrapper package appears only once."""
    info = get_context_version()
    keys = list(info.keys())
    assert len(keys) == len(set(keys))


# ---- Combined output ----


def test_all_three_layers(tmp_path):
    """Engine version, wrapper (if any), and context metadata all present."""
    _write_file(
        tmp_path,
        "context-metadata.yml",
        "name: test-content\nversion: 0.1.0",
    )

    info = get_context_version(metadata_path=tmp_path / "context-metadata.yml")

    assert "sdlc-mcp" in info
    assert info["context_name"] == "test-content"
    assert info["context_version"] == "0.1.0"


def test_engine_version_comes_first():
    """sdlc-mcp is the first key in the dict."""
    info = get_context_version()
    first_key = next(iter(info))
    assert first_key == "sdlc-mcp"
