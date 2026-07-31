# Changelog

All notable changes to the Durin Home Assistant integration are documented here.

## [0.7.0-dev] - 2026-07-31

### Added
- **Untested, in-progress:** Durin Options screen now lets you pick devices instead of raw entities. Entities that need to sync are derived automatically from the device's non-diagnostic entities. Has not yet been verified against a live Home Assistant instance

---

## [0.6.9] - 2026-07-30

### Fixed
- MQTT connection was dropping and reconnecting every 30-90 minutes (disconnectReason CONNECTION_LOST/MQTT_KEEP_ALIVE_TIMEOUT), causing spurious "offline then immediately back online" status. The SDK's 3-second ping timeout combined with a 30-second keep-alive left no margin for normal network jitter. Widened keep-alive to 60s and set an explicit 10-second ping timeout

---

## [0.6.8] - 2026-07-27

### Fixed
- An explicit device rename (`name_by_user`) was being ignored in favor of a guessed entity-derived name for any device on a network with a Zigbee coordinator/bridge. The user-set name now always takes priority

---

## [0.6.7] - 2026-07-27

### Fixed
- Device name fallback picked whichever entity's full friendly name was shortest (e.g. "...Battery" beating "...Temperature" by one character) instead of the shared device-level prefix across all its entities. Now derives the name from the common leading words, e.g. "Attic Env Sensor 6" instead of "Attic Env Sensor 6 Battery"

---

## [0.6.6] - 2026-07-27

### Fixed
- Devices whose via_device_id points at themselves (a self-referencing "bridge" marker some integrations use) caused device_representation() to recurse into itself forever, silently crashing the name resync with no log output at all. This is why some devices' renames never produced any trace in the logs

---

## [0.6.5] - 2026-07-27

### Fixed
- Filtering device registry events by changed-field name (0.6.4) most likely suppressed real renames on some devices with no log trace at all. Replaced with a per-device cache of the last name actually synced, so the resync always attempts on any registry update but only calls the cloud when the computed name actually differs

---

## [0.6.4] - 2026-07-27

### Fixed
- Device registry update events were treated as renames regardless of which field changed, so an HA restart's registry reconciliation flooded the resync path for unrelated devices. Now only reacts when the changed fields actually include the device name

---

## [0.6.3] - 2026-07-27

### Fixed
- Device name resync only detected renames via entity `friendly_name` changes, which many integrations (e.g. Zigbee/LUMI sensors) never update on a device rename. Now listens to Home Assistant's device registry update event directly, so renames are detected regardless of integration pattern

---

## [0.6.2] - 2026-07-27

### Fixed
- Device name resync (added in 0.6.0) never actually reached the cloud, because it looked up devices under Durin's own config entry instead of the entry of the integration that actually owns the device (ZHA, MQTT, etc.)

---

## [0.6.1] - 2026-07-27

### Changed
- `mapped_entities` in the Durin Options screen is now an editable multi-select entity picker instead of a read-only, truncated comma-joined string

---

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
