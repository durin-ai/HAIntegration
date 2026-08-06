"""Lock entities reflecting Durin Threshold zones, with real lock/unlock control."""

from __future__ import annotations

import logging

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .durin_spaces import DOMAIN, LOCK_ZONE_TYPES, space_device_identifiers, zone_space_pairs

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    durin = hass.data[DOMAIN][entry.entry_id]["durin"]
    known: set[str] = set()

    def _add_new_entities() -> None:
        new_entities = []
        for zone, space in zone_space_pairs(coordinator.data, LOCK_ZONE_TYPES):
            unique_id = f"zone:{zone['zoneId']}:{space['spaceId']}"
            if unique_id in known:
                continue
            known.add(unique_id)
            new_entities.append(DurinZoneLock(coordinator, durin, zone["zoneId"], space["spaceId"]))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))
    _add_new_entities()


class DurinZoneLock(CoordinatorEntity, LockEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, durin, zone_id: str, space_id: str) -> None:
        super().__init__(coordinator)
        self._durin = durin
        self._zone_id = zone_id
        self._space_id = space_id
        self._attr_unique_id = f"zone:{zone_id}:{space_id}"
        self._attr_device_info = {"identifiers": space_device_identifiers(space_id)}

    @property
    def _zone(self) -> dict | None:
        return self.coordinator.data.get("zones", {}).get(self._zone_id)

    @property
    def available(self) -> bool:
        return super().available and self._zone is not None

    @property
    def name(self) -> str | None:
        zone = self._zone
        return zone["name"] if zone else None

    @property
    def is_locked(self) -> bool | None:
        zone = self._zone
        if zone is None:
            return None
        state = zone.get("aptitudes", {}).get("lock", {}).get("state")
        if state is None or state == "unknown":
            return None
        return state == "locked"

    @property
    def extra_state_attributes(self):
        zone = self._zone
        if zone is None:
            return None
        attrs = dict(zone.get("aptitudes", {}).get("lock", {}))
        attrs.pop("state", None)
        return attrs

    async def _async_send(self, operation: str) -> None:
        response = await self._durin.SendCloudCommand(
            "zone_operation", {"zoneId": self._zone_id, "operation": operation}
        )
        if response is None or response.get("status") != "COMPLETE":
            raise HomeAssistantError(f"Durin {operation} failed for zone {self._zone_id}: {response}")
        await self.coordinator.async_request_refresh()

    async def async_lock(self, **kwargs) -> None:
        await self._async_send("lock")

    async def async_unlock(self, **kwargs) -> None:
        await self._async_send("unlock")
