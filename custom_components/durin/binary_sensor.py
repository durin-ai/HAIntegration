"""Binary sensor entities reflecting Durin motion/occupancy zones."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .durin_spaces import (
    BINARY_SENSOR_ZONE_TYPES,
    DOMAIN,
    MOTION_ZONE_TYPE,
    OCCUPANCY_ZONE_TYPE,
    space_device_identifiers,
    zone_space_pairs,
)

_LOGGER = logging.getLogger(__name__)

ZONE_STATE_ON = {
    MOTION_ZONE_TYPE: "detected",
    OCCUPANCY_ZONE_TYPE: "occupied",
}
ZONE_DEVICE_CLASS = {
    MOTION_ZONE_TYPE: BinarySensorDeviceClass.MOTION,
    OCCUPANCY_ZONE_TYPE: BinarySensorDeviceClass.OCCUPANCY,
}
ZONE_APTITUDE_KEY = {
    MOTION_ZONE_TYPE: "motion",
    OCCUPANCY_ZONE_TYPE: "occupancy",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    known: set[str] = set()

    def _add_new_entities() -> None:
        new_entities = []
        for zone, space in zone_space_pairs(coordinator.data, BINARY_SENSOR_ZONE_TYPES):
            unique_id = f"zone:{zone['zoneId']}:{space['spaceId']}"
            if unique_id in known:
                continue
            known.add(unique_id)
            new_entities.append(DurinZoneBinarySensor(coordinator, zone["zoneId"], space["spaceId"]))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))
    _add_new_entities()


class DurinZoneBinarySensor(CoordinatorEntity, BinarySensorEntity):
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
    def device_class(self):
        zone = self._zone
        return ZONE_DEVICE_CLASS.get(zone["type"]) if zone else None

    @property
    def is_on(self) -> bool | None:
        zone = self._zone
        if zone is None:
            return None
        aptitude_key = ZONE_APTITUDE_KEY[zone["type"]]
        state = zone.get("aptitudes", {}).get(aptitude_key, {}).get("state")
        return None if state is None else state == ZONE_STATE_ON[zone["type"]]

    @property
    def extra_state_attributes(self):
        zone = self._zone
        if zone is None:
            return None
        aptitude_key = ZONE_APTITUDE_KEY[zone["type"]]
        attrs = dict(zone.get("aptitudes", {}).get(aptitude_key, {}))
        attrs.pop("state", None)
        return attrs
