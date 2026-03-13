---
description: "Bump the Durin integration version (major or minor), update CHANGELOG, commit and push — GitHub Actions will automatically create the release."
name: "Bump Version"
argument-hint: "major or minor"
agent: "agent"
---

Bump the Durin integration version. The bump type requested is: **$ARGUMENTS**

Follow these steps:

1. **Validate input** — `$ARGUMENTS` must be either `major` or `minor`. If it's anything else, stop and ask.

2. **Read current version** — read the `"version"` field from [custom_components/durin/manifest.json](../../custom_components/durin/manifest.json). It follows `MAJOR.MINOR.PATCH` semver.

3. **Calculate new version**:
   - `major` → increment MAJOR, reset MINOR and PATCH to 0 (e.g. `1.3.2` → `2.0.0`)
   - `minor` → increment MINOR, reset PATCH to 0 (e.g. `1.3.2` → `1.4.0`)

4. **Ask the user what changed** — ask for a brief summary of what's new in this release (Added / Fixed / Changed / Removed). Wait for their response before continuing.

5. **Update CHANGELOG** — prepend a new section to [CHANGELOG.md](../../CHANGELOG.md):
   ```
   ## [X.Y.0] - YYYY-MM-DD

   ### Added / Fixed / Changed / Removed
   - <user's notes>

   ---
   ```

6. **Bump version** — update `"version"` in [custom_components/durin/manifest.json](../../custom_components/durin/manifest.json) to the new version.

7. **Commit and push** — stage both files and commit:
   ```
   chore: bump version to X.Y.0
   ```
   Then push to `main`.

8. **Confirm** — tell the user the new version, and that GitHub Actions will automatically create the release at https://github.com/durin-ai/HAIntegration/actions. HACS will notify users once the release is published.
