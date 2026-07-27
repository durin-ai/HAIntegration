# Changelog

All notable changes to the Durin Home Assistant integration are documented here.

## [0.6.0] - 2026-07-27

### Added
- Device names are now resynced automatically when renamed in Home Assistant, instead of only being set once at initial import

### Fixed
- README updated for the current HACS UI (no more separate "Integrations" tab) and to reflect the real `XXXX-XXXX` access code format instead of the old 6-digit design

---

## [0.5.0] - 2026-07-27

### Fixed
- MQTT connection wasn't torn down on integration unload, causing a stale connection to fight a reloaded one over the same AWS IoT client ID (repeated `DUPLICATE_CLIENTID` disconnects that looked like device flapping)
- `EVENT_STATE_CHANGED` listener leak on MQTT reconnect
- Device name resolution for bridged/nested devices
- Config flow strings still described an old 6-digit numeric code format; updated to reflect the real `XXXX-XXXX` alphanumeric access code
- Icon rendering (dark background, rounded corners) for visibility in HACS and HA UI

---

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
