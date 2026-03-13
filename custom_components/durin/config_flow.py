from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

import logging
_LOGGER = logging.getLogger(__name__)


DOMAIN="ha_durin_integration"

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("residence_code"): str,
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
        _LOGGER.warning("DurinOptionsFlow base classes: %s", DurinOptionsFlow.__mro__)
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            # Nothing is user-editable; keep existing options
            return self.async_create_entry(data=self._config_entry.options)

        fields: dict = {}

        # One read-only field per programmatic option
        for key in self._config_entry.options.keys():
            fields[vol.Optional(key)] = TextSelector(
                TextSelectorConfig(read_only=True)
            )

        options_schema = vol.Schema(fields)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                options_schema,
                self._config_entry.options,
            ),
        )