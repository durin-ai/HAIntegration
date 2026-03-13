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

6. **Create GitHub release** — extract the changelog section for this version and pass it as the release notes:
   ```sh
   gh release create v$ARGUMENTS --title "v$ARGUMENTS" --notes-file <(awk '/^## \[$ARGUMENTS\]/,/^---/' CHANGELOG.md | head -n -2)
   ```
   This tags the commit and publishes a release. HACS checks GitHub releases to detect updates, so this is what triggers the "update available" badge in Home Assistant.

7. **Confirm** — report the release URL and remind the user that Home Assistant instances with the integration installed will see the update notification after their next HACS refresh (usually within 24 hours, or immediately via HACS → Check for updates).
