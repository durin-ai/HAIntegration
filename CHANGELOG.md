# Changelog

All notable changes to the Durin Home Assistant integration are documented here.

## [0.4.0] - 2026-03-13

### Changed
- Minimum required Home Assistant version set to `2026.3.0` (the version actively tested and confirmed working)

---

## [0.3.0] - 2026-03-13

### Added
- Durin logo icon for HACS store listing and HA integrations UI

### Fixed
- Minimum Home Assistant version requirement corrected to 2024.1.0 (was incorrectly set to 2026.3.0, which prevented HACS from showing updates)

---

## [0.2.0] - 2026-03-13

### Added
- `strings.json` and `translations/en.json` for config flow UI labels
- GitHub releases workflow for HACS update detection

### Fixed
- Removed `content_in_root` from `hacs.json` so HACS correctly downloads from `custom_components/durin/`
- Fixed placeholder `documentation` and `issue_tracker` URLs in `manifest.json`

---

## [0.1.0] - 2026-03-13

### Added
- Initial release of the Durin Ecosystem Home Assistant integration
- MQTT connection to Durin cloud via AWS IoT Core
- Config flow using 6-digit Durin residence code from the mobile app
- HACS-compatible repository structure
