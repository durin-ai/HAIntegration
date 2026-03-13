---
description: "Create a new versioned release for the Durin HA integration — bumps the version in manifest.json, commits, tags, pushes, and creates a GitHub release so Home Assistant flags an update via HACS."
name: "Create Release"
argument-hint: "New version number, e.g. 0.2.0"
agent: "agent"
---

Create a new release for the Durin Home Assistant integration. The version to release is: **$ARGUMENTS**

Follow these steps in order:

1. **Validate input** — confirm `$ARGUMENTS` is a valid semver string (e.g. `0.2.0`). If not, stop and ask for a valid version.

2. **Bump version** — update the `"version"` field in [custom_components/durin/manifest.json](../../custom_components/durin/manifest.json) to `$ARGUMENTS`.

3. **Update CHANGELOG** — add a new section at the top of [CHANGELOG.md](../../CHANGELOG.md) for `[$ARGUMENTS] - <today's date>`. Ask the user what changed (Added / Fixed / Changed / Removed), then fill it in. This content will become the GitHub release body.

4. **Commit** — stage `manifest.json` and `CHANGELOG.md` and commit with the message:
   ```
   chore: bump version to $ARGUMENTS
   ```

5. **Push** — push the commit to `main`.

6. **Done** — the GitHub Actions workflow (`.github/workflows/auto-release.yml`) will automatically detect the version change in `manifest.json`, extract the changelog notes for this version, and create the GitHub release. This triggers the "update available" badge in HACS for all users.

7. **Confirm** — let the user know the push is done and they can monitor the release at https://github.com/durin-ai/HAIntegration/actions to watch the workflow complete.
