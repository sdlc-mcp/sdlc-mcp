"""Integration tests for the stdio transport path.

These tests spawn the server as a subprocess via StdioTransport,
exercising the full CLI entry point, config loading with path
resolution, and MCP tool calls end-to-end.
"""

import asyncio
import sys

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def _run(coro):
    return asyncio.run(coro)


def _make_config(tmp_path, scopes_yaml: str) -> str:
    config_file = tmp_path / "config.yml"
    config_file.write_text(scopes_yaml)
    return str(config_file)


def _make_client(config_path: str) -> Client:
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "sdlc_mcp", "serve", "--config", config_path],
    )
    return Client(transport)


def _write_md(directory, name, description, body):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.md").write_text(
        f'---\nname: {name}\ndescription: "{description}"\n---\n{body}\n'
    )


@pytest.fixture()
def example_config(tmp_path):
    org_dir = tmp_path / "content" / "org"
    team_dir = tmp_path / "content" / "teams" / "api"

    _write_md(org_dir, "testing", "Org testing", "# Org Testing\n80% coverage.")
    _write_md(org_dir, "code-review", "Code review", "# Code Review\nReview all PRs.")
    _write_md(team_dir, "testing", "API testing", "# API Testing\n90% coverage.")

    config_path = _make_config(
        tmp_path,
        """
- name: platform
  sources:
    - type: local
      path: content/org/

- name: api
  repos: [api-gateway]
  sources:
    - type: local
      path: content/teams/api/
""",
    )
    return config_path


class TestStdioListTools:
    def test_tools_are_registered(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                tools = await client.list_tools()
                names = {t.name for t in tools}
                assert "testing" in names
                assert "code_review" in names

        _run(run())

    def test_tool_descriptions_from_frontmatter(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                tools = {t.name: t for t in await client.list_tools()}
                assert "API testing" in tools["testing"].description

        _run(run())


class TestStdioCallTools:
    def test_team_override(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                result = await client.call_tool("testing", {"repo": "api-gateway"})
                text = result.content[0].text
                assert "90%" in text
                assert "API Testing" in text

        _run(run())

    def test_org_fallback_for_unknown_repo(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                result = await client.call_tool("testing", {"repo": "unknown"})
                text = result.content[0].text
                assert "80%" in text
                assert "Org Testing" in text

        _run(run())

    def test_tool_with_no_repo(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                result = await client.call_tool("code_review", {})
                text = result.content[0].text
                assert "Code Review" in text

        _run(run())


class TestStdioDiscoveryTools:
    def test_list_repos_registered(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                tools = await client.list_tools()
                names = {t.name for t in tools}
                assert "list_repos" in names

        _run(run())

    def test_list_tools_for_repo_registered(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                tools = await client.list_tools()
                names = {t.name for t in tools}
                assert "list_tools_for_repo" in names

        _run(run())

    def test_list_repos_returns_scoped_repos(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                result = await client.call_tool("list_repos", {})
                text = result.content[0].text
                assert "api-gateway" in text

        _run(run())

    def test_list_repos_excludes_unscoped(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                result = await client.call_tool("list_repos", {})
                text = result.content[0].text
                assert "platform" not in text

        _run(run())

    def test_list_tools_for_known_repo(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                result = await client.call_tool("list_tools_for_repo", {"repo": "api-gateway"})
                text = result.content[0].text
                assert "testing" in text
                assert "code-review" in text

        _run(run())

    def test_list_tools_for_repo_shows_override(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                result = await client.call_tool("list_tools_for_repo", {"repo": "api-gateway"})
                text = result.content[0].text
                # testing is overridden by api scope, should indicate that
                assert "api" in text
                assert "platform" in text

        _run(run())

    def test_list_tools_for_unknown_repo(self, example_config):
        async def run():
            async with _make_client(example_config) as client:
                result = await client.call_tool("list_tools_for_repo", {"repo": "unknown-repo"})
                text = result.content[0].text
                assert "testing" in text
                assert "code-review" in text

        _run(run())


class TestStdioExampleConfig:
    """Verify the shipped examples/simple/config.yml works end-to-end."""

    def test_example_config_loads(self):
        async def run():
            transport = StdioTransport(
                command=sys.executable,
                args=["-m", "sdlc_mcp", "serve", "--config", "examples/simple/config.yml"],
            )
            async with Client(transport) as client:
                tools = await client.list_tools()
                names = {t.name for t in tools}
                assert "testing" in names
                assert "code_review" in names
                assert len(tools) >= 2

        _run(run())
