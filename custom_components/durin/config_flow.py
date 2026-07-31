from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    DeviceSelector,
    DeviceSelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

import logging
_LOGGER = logging.getLogger(__name__)


DOMAIN="ha_durin_integration"

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("residence_code"): str,
    }
)


def _entities_for_devices(hass, device_ids):
    """Primary (non-diagnostic, non-config, enabled) entities for the given devices.

    HA's own entity_category already distinguishes "this is diagnostic/config"
    (signal strength, restart buttons, firmware entities, etc.) from the
    entities that carry real state, so a user picking a device doesn't need to
    know or care which of its entities actually matter to sync.
    """
    entity_registry = er.async_get(hass)
    return sorted(
        {
            ent.entity_id
            for ent in entity_registry.entities.values()
            if ent.device_id in device_ids
            and ent.entity_category is None
            and ent.disabled_by is None
        }
    )


class MyIntegrationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for My Integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # No complex validation; just store the string
            return self.async_create_entry(
                title="Durin Residence Code",  # or a fixed title
                data={"residence_code": user_input["residence_code"]},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors={},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return DurinOptionsFlow(config_entry)

class DurinOptionsFlow(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            device_ids = sorted(user_input.get("mapped_devices", []))
            new_options = {
                **self._config_entry.options,
                "mapped_devices": device_ids,
                "mapped_entities": _entities_for_devices(self.hass, set(device_ids)),
            }
            return self.async_create_entry(title="", data=new_options)

        fields: dict = {}

        # One read-only field per programmatic option that isn't user-editable
        for key in self._config_entry.options.keys():
            if key in ("mapped_entities", "mapped_devices"):
                continue
            fields[vol.Optional(key)] = TextSelector(
                TextSelectorConfig(read_only=True)
            )

        # Users pick devices, not entities - the entities that actually need to
        # sync are derived automatically (see _entities_for_devices above).
        fields[vol.Optional("mapped_devices")] = DeviceSelector(
            DeviceSelectorConfig(multiple=True)
        )

        options_schema = vol.Schema(fields)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                options_schema,
                self._config_entry.options,
            ),
        )
