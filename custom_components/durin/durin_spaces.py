"""Shared helpers for mapping Durin spaces/zones onto Home Assistant areas/floors/devices."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import floor_registry as fr

DOMAIN = "ha_durin_integration"

LEVEL_SPACE_TYPE = "Level"

MOTION_ZONE_TYPE = "MotionZone"
OCCUPANCY_ZONE_TYPE = "OccupancyZone"
THRESHOLD_ZONE_TYPE = "ThresholdZone"

BINARY_SENSOR_ZONE_TYPES = {MOTION_ZONE_TYPE, OCCUPANCY_ZONE_TYPE}
LOCK_ZONE_TYPES = {THRESHOLD_ZONE_TYPE}


def space_device_identifiers(space_id: str) -> set[tuple[str, str]]:
    return {(DOMAIN, f"space:{space_id}")}


def _level_ancestor(spaces: dict, space: dict) -> dict | None:
    """Nearest Level-type ancestor of `space` by walking parentSpace, or None."""
    parent_id = space.get("parentSpace")
    while parent_id:
        parent = spaces.get(parent_id)
        if parent is None:
            return None
        if parent.get("type") == LEVEL_SPACE_TYPE:
            return parent
        parent_id = parent.get("parentSpace")
    return None


def sync_areas_and_devices(hass: HomeAssistant, entry: ConfigEntry, spaces: dict) -> None:
    """Ensure every Durin space has a matching HA area (+ floor, if under a Level) and device.

    Every space maps 1:1 to its own flat HA area. Spaces nested under a Level-type
    space additionally get that Level's HA floor assigned, so Floors/Areas roughly
    mirror the Level/Room hierarchy even though the area mapping itself stays flat.
    Durin is the system of record for these devices, so area assignment is pinned
    on every sync rather than left to drift if someone reassigns it manually.
    """
    area_registry = ar.async_get(hass)
    floor_registry = fr.async_get(hass)
    device_registry = dr.async_get(hass)

    for space in spaces.values():
        area = area_registry.async_get_or_create(space["name"])

        if space.get("type") != LEVEL_SPACE_TYPE:
            level = _level_ancestor(spaces, space)
            if level is not None:
                floor = floor_registry.async_get_or_create(level["name"])
                if area.floor_id != floor.floor_id:
                    area = area_registry.async_update(area.id, floor_id=floor.floor_id)

        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers=space_device_identifiers(space["spaceId"]),
            name=space["name"],
            suggested_area=area.name,
        )
        if device.area_id != area.id:
            device_registry.async_update_device(device.id, area_id=area.id)


def zone_space_pairs(coordinator_data: dict | None, zone_types: set[str]):
    """Yield (zone, space) for every zone of the given type(s) linked to a known space."""
    data = coordinator_data or {}
    spaces = data.get("spaces", {})
    zones = data.get("zones", {})
    for zone in zones.values():
        if zone.get("type") not in zone_types:
            continue
        for space_id in zone.get("spaceIds", []):
            space = spaces.get(space_id)
            if space is not None:
                yield zone, space


def unhandled_zone_space_pairs(coordinator_data: dict | None, handled_zone_types: set[str]):
    """Yield (zone, space) for every zone whose type isn't in `handled_zone_types`."""
    data = coordinator_data or {}
    spaces = data.get("spaces", {})
    zones = data.get("zones", {})
    for zone in zones.values():
        if zone.get("type") in handled_zone_types:
            continue
        for space_id in zone.get("spaceIds", []):
            space = spaces.get(space_id)
            if space is not None:
                yield zone, space
