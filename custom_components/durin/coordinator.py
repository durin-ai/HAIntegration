"""Coordinator for Durin space/zone data pulled down from the cloud."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .durin_spaces import sync_areas_and_devices

_LOGGER = logging.getLogger(__name__)

SYNC_INTERVAL = timedelta(minutes=5)


class DurinSpaceZoneCoordinator(DataUpdateCoordinator):
    """Holds the latest Durin space/zone tree, refreshed via the get_spaces_zones cloud command.

    There's no cloud-side change-notification path for space/zone edits yet, so this
    polls on SYNC_INTERVAL; DurinIoT also triggers an out-of-band refresh once the MQTT
    connection actually comes up (see on_shadow_get_accepted_safe), so data doesn't wait
    a full interval after a fresh start/reconnect.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, durin) -> None:
        super().__init__(hass, _LOGGER, name="Durin space/zone sync", update_interval=SYNC_INTERVAL)
        self.entry = entry
        self.durin = durin

    async def _async_update_data(self):
        response = await self.durin.SendCloudCommand("get_spaces_zones", {})
        if response is None or response.get("status") != "COMPLETE":
            raise UpdateFailed(f"get_spaces_zones failed: {response}")

        result = response.get("result") or {}
        spaces = {space["spaceId"]: space for space in result.get("spaces", [])}
        zones = {zone["zoneId"]: zone for zone in result.get("zones", [])}

        sync_areas_and_devices(self.hass, self.entry, spaces)

        return {"spaces": spaces, "zones": zones}
