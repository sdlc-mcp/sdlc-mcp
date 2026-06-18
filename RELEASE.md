# Release Process

## Overview

Releases are automated via GitHub Actions. The version number is generated automatically using CalVer (`YYYY.MM.DD`) via `setuptools-scm`. To cut a release, you tag a commit and push the tag. The rest happens automatically.

## Pre-Release Checklist

Before creating a release tag:

1. **Run tests locally**
   ```bash
   uv run pytest
   ```

2. **Run linters**
   ```bash
   uvx ruff check .
   uvx ruff format --check .
   ```

3. **Verify the package builds**
   ```bash
   uv build
   ```

4. **Test installation from local build**
   ```bash
   pip install dist/sdlc_mcp-*.whl
   sdlc-mcp --help
   ```

5. **Check that all PRs intended for this release are merged**

6. **Update CLAUDE.md or README.md if needed** (new features, breaking changes, etc.)

## Creating a Release

### Option 1: Manual Tag (Command Line)

1. **Ensure you're on the main branch with the latest commits**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create and push a version tag**
   
   The tag should be in the format `vYYYY.MM.DD`. If you need multiple releases in one day, append a sequence number: `vYYYY.MM.DD.N`.
   
   ```bash
   # Today's date (2026-06-18)
   git tag v2026.06.18
   git push origin v2026.06.18
   ```

3. **Monitor the release workflow**
   
   Go to https://github.com/shanemcd/sdlc-mcp/actions and watch the "Release" workflow.

### Option 2: GitHub UI (Workflow Dispatch)

1. **Navigate to the Actions tab**
   
   Go to https://github.com/shanemcd/sdlc-mcp/actions/workflows/release.yml

2. **Click "Run workflow"**

3. **Fill in the inputs:**
   - **ref:** Leave empty to tag HEAD of main, or specify a commit SHA or branch name
   - **tag:** Enter the tag name (e.g., `v2026.06.18`)

4. **Click "Run workflow"**

The workflow will:
- Check out the specified ref (or HEAD of main if empty)
- Create and push the tag
- Build the package
- Publish to PyPI
- Create a GitHub Release with auto-generated release notes

## Post-Release Verification

1. **Verify PyPI publication**
   
   Check https://pypi.org/project/sdlc-mcp/ to confirm the new version appears.

2. **Test installation from PyPI**
   ```bash
   pip install --upgrade sdlc-mcp
   sdlc-mcp --version
   ```

3. **Check the GitHub Release**
   
   Visit https://github.com/shanemcd/sdlc-mcp/releases to verify the release notes look correct.

## Troubleshooting

**If the workflow fails:**

1. Check the workflow logs at https://github.com/shanemcd/sdlc-mcp/actions
2. Common issues:
   - Build failures (tests, linting)
   - PyPI authentication issues (check repository secrets)
   - Tag already exists on PyPI (can't overwrite, must use a new version)

**If you need to cancel a release:**

If the tag was pushed but the workflow hasn't completed:
1. Cancel the workflow in the GitHub Actions UI
2. Delete the tag locally and remotely:
   ```bash
   git tag -d v2026.06.18
   git push origin :refs/tags/v2026.06.18
   ```

Note: If the package was already published to PyPI, you cannot unpublish it. You'll need to publish a new patch version instead.

## Versioning

This project uses CalVer (Calendar Versioning):
- Format: `YYYY.MM.DD` (e.g., `2026.06.18`)
- Multiple releases in one day: `YYYY.MM.DD.N` (e.g., `2026.06.18.1`)
- Version is determined automatically by `setuptools-scm` based on the git tag

The tag format must start with `v` (e.g., `v2026.06.18`) to trigger the release workflow.
