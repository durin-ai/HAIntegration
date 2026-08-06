"""Generic sensor entities for Durin zone types not covered by binary_sensor/lock.

Covers Climate, Environmental, Lighting, Security, Access, Recording and General
zones, which don't yet have well-defined live-state semantics the way Motion,
Occupancy and Threshold zones do. As those types grow real fields, move them into
a dedicated platform (see binary_sensor.py/lock.py) instead of special-casing here.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .durin_spaces import (
    BINARY_SENSOR_ZONE_TYPES,
    DOMAIN,
    LOCK_ZONE_TYPES,
    space_device_identifiers,
    unhandled_zone_space_pairs,
)

_LOGGER = logging.getLogger(__name__)

HANDLED_ZONE_TYPES = BINARY_SENSOR_ZONE_TYPES | LOCK_ZONE_TYPES


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    known: set[str] = set()

    def _add_new_entities() -> None:
        new_entities = []
        for zone, space in unhandled_zone_space_pairs(coordinator.data, HANDLED_ZONE_TYPES):
            unique_id = f"zone:{zone['zoneId']}:{space['spaceId']}"
            if unique_id in known:
                continue
            known.add(unique_id)
            new_entities.append(DurinZoneSensor(coordinator, zone["zoneId"], space["spaceId"]))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))
    _add_new_entities()


class DurinZoneSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, zone_id: str, space_id: str) -> None:
        super().__init__(coordinator)
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
    def native_value(self):
        zone = self._zone
        return zone["type"] if zone else None

    @property
    def extra_state_attributes(self):
        zone = self._zone
        return dict(zone.get("aptitudes", {})) if zone else None
