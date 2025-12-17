"""Config flow for Durin Ecosystem integration."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
import re

import async_timeout
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector, entity_registry as er

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_MQTT_BROKER,
    DEFAULT_MQTT_PORT,
    DEFAULT_USE_TLS,
    CONF_DURIN_CODE,
    CONF_MQTT_BROKER,
    CONF_MQTT_PORT,
    CONF_MQTT_USERNAME,
    CONF_MQTT_PASSWORD,
    CONF_INSTALLATION_ID,
    CONF_USE_TLS,
    CONF_SELECTED_ENTITIES,
    CONF_SYNC_ALL_ENTITIES,
    CONF_IMPORT_SPACES,
    SUPPORTED_DOMAINS,
    MQTT_TIMEOUT,
    ERROR_INVALID_CODE,
    ERROR_CODE_EXPIRED,
    ERROR_CONNECTION_FAILED,
)

_LOGGER = logging.getLogger(__name__)


def _get_user_schema(defaults: Dict[str, Any] = None) -> vol.Schema:
    """Build the user step schema with proper defaults."""
    defaults = defaults or {}
    return vol.Schema({
        vol.Required(
            CONF_NAME,
            default=defaults.get(CONF_NAME, DEFAULT_NAME),
        ): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
        vol.Required(CONF_DURIN_CODE): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
    })


def _get_reauth_schema() -> vol.Schema:
    """Build the reauth step schema."""
    return vol.Schema({
        vol.Required(CONF_DURIN_CODE): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
    })


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Durin Ecosystem."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    def __init__(self):
        """Initialize the config flow."""
        self._durin_code: Optional[str] = None
        self._name: Optional[str] = None
        self._installation_id: Optional[str] = None
        self._mqtt_config: Optional[Dict[str, Any]] = None
        self._selected_entities: List[str] = []
        self._sync_all: bool = False
        self._import_spaces: bool = False

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Step 1: Handle the initial step - Durin code and name."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._durin_code = user_input[CONF_DURIN_CODE].strip()
            self._name = user_input[CONF_NAME]

            # Validate the 6-digit Durin code
            try:
                self._mqtt_config = await self._validate_durin_code(self._durin_code)
            except InvalidCode:
                errors["base"] = ERROR_INVALID_CODE
            except CodeExpired:
                errors["base"] = ERROR_CODE_EXPIRED
            except CannotConnect:
                errors["base"] = ERROR_CONNECTION_FAILED
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during setup")
                errors["base"] = "unknown"
            else:
                # Code validated, proceed to device selection
                self._installation_id = self._mqtt_config.get(CONF_INSTALLATION_ID)
                await self.async_set_unique_id(self._installation_id)
                self._abort_if_unique_id_configured()
                return await self.async_step_devices()

        return self.async_show_form(
            step_id="user",
            data_schema=_get_user_schema(),
            errors=errors,
        )

    async def async_step_devices(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Step 2: Select devices to synchronize with Durin."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._sync_all = user_input.get(CONF_SYNC_ALL_ENTITIES, False)
            
            if self._sync_all:
                # Get all supported entities
                self._selected_entities = await self._get_all_supported_entities()
            else:
                self._selected_entities = user_input.get(CONF_SELECTED_ENTITIES, [])
            
            # Proceed to spaces step
            return await self.async_step_spaces()

        # Get available entities for selection
        entity_list = await self._get_all_supported_entities()
        
        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema({
                vol.Required(CONF_SYNC_ALL_ENTITIES, default=True): selector.BooleanSelector(),
                vol.Optional(CONF_SELECTED_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=SUPPORTED_DOMAINS,
                        multiple=True,
                    )
                ),
            }),
            errors=errors,
            description_placeholders={
                "entity_count": str(len(entity_list)),
            },
        )

    async def async_step_spaces(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Step 3: Ask about importing Durin spaces."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._import_spaces = user_input.get(CONF_IMPORT_SPACES, False)
            # Proceed to completion
            return await self.async_step_complete()

        return self.async_show_form(
            step_id="spaces",
            data_schema=vol.Schema({
                vol.Required(CONF_IMPORT_SPACES, default=True): selector.BooleanSelector(),
            }),
            errors=errors,
        )

    async def async_step_complete(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Step 4: Complete the setup."""
        # Create the config entry with all collected data
        return self.async_create_entry(
            title=self._name,
            data={
                CONF_DURIN_CODE: self._durin_code,
                CONF_NAME: self._name,
                CONF_INSTALLATION_ID: self._installation_id,
                CONF_MQTT_BROKER: self._mqtt_config[CONF_MQTT_BROKER],
                CONF_MQTT_PORT: self._mqtt_config[CONF_MQTT_PORT],
                CONF_MQTT_USERNAME: self._mqtt_config[CONF_MQTT_USERNAME],
                CONF_MQTT_PASSWORD: self._mqtt_config[CONF_MQTT_PASSWORD],
                CONF_USE_TLS: self._mqtt_config.get(CONF_USE_TLS, True),
                CONF_SYNC_ALL_ENTITIES: self._sync_all,
                CONF_SELECTED_ENTITIES: self._selected_entities,
                CONF_IMPORT_SPACES: self._import_spaces,
            },
        )

    async def _get_all_supported_entities(self) -> List[str]:
        """Get all entities from supported domains."""
        entity_reg = er.async_get(self.hass)
        entities = []
        
        for entity in entity_reg.entities.values():
            domain = entity.entity_id.split(".")[0]
            if domain in SUPPORTED_DOMAINS and not entity.disabled:
                entities.append(entity.entity_id)
        
        return sorted(entities)

    async def async_step_reauth(self, entry_data: Dict[str, Any]) -> FlowResult:
        """Handle reauthorization."""
        self._name = entry_data.get(CONF_NAME, DEFAULT_NAME)
        
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Confirm reauthorization."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._durin_code = user_input[CONF_DURIN_CODE].strip()

            try:
                self._mqtt_config = await self._validate_durin_code(self._durin_code)
            except InvalidCode:
                errors["base"] = ERROR_INVALID_CODE
            except CodeExpired:
                errors["base"] = ERROR_CODE_EXPIRED
            except CannotConnect:
                errors["base"] = ERROR_CONNECTION_FAILED
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                # Update the existing entry
                installation_id = self._mqtt_config.get(CONF_INSTALLATION_ID)
                entry = await self.async_set_unique_id(installation_id)
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_DURIN_CODE: self._durin_code,
                        CONF_MQTT_BROKER: self._mqtt_config[CONF_MQTT_BROKER],
                        CONF_MQTT_PORT: self._mqtt_config[CONF_MQTT_PORT],
                        CONF_MQTT_USERNAME: self._mqtt_config[CONF_MQTT_USERNAME],
                        CONF_MQTT_PASSWORD: self._mqtt_config[CONF_MQTT_PASSWORD],
                        CONF_USE_TLS: self._mqtt_config.get(CONF_USE_TLS, True),
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_get_reauth_schema(),
            errors=errors,
        )

    @staticmethod
    @core.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def _validate_durin_code(self, code: str) -> Dict[str, Any]:
        """Validate the 6-digit Durin code and retrieve MQTT configuration."""
        _LOGGER.debug("Validating Durin code")
        
        # Validate format: 6 digits
        if not re.match(r'^\d{6}$', code):
            _LOGGER.error("Invalid code format: must be 6 digits")
            raise InvalidCode("Code must be 6 digits")
        
        # TODO: Call Durin backend API to validate code and get MQTT config
        # For now, using placeholder logic
        try:
            async with async_timeout.timeout(MQTT_TIMEOUT):
                # Placeholder: In production, this would call the Durin backend API
                # Example: POST https://durin-api.example.com/v1/validate-code
                # Response would include: installation_id, mqtt_broker, mqtt_port, 
                # mqtt_username, mqtt_password, use_tls
                
                # Temporary mock response
                mqtt_config = {
                    CONF_INSTALLATION_ID: f"durin-{code}",
                    CONF_MQTT_BROKER: DEFAULT_MQTT_BROKER,
                    CONF_MQTT_PORT: DEFAULT_MQTT_PORT,
                    CONF_MQTT_USERNAME: f"user-{code}",
                    CONF_MQTT_PASSWORD: f"pass-{code}",
                    CONF_USE_TLS: DEFAULT_USE_TLS,
                }
                
                _LOGGER.info("Code validated successfully")
                return mqtt_config
                
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout validating Durin code")
            raise CannotConnect("Timeout connecting to Durin backend") from err
        except Exception as err:
            _LOGGER.error("Error validating code: %s", err)
            raise CannotConnect(f"Validation error: {err}") from err


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        # No options to configure - all settings come from Durin backend
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "info": "Configuration is managed through the Durin platform. Use a new code to reconfigure."
            }
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidCode(exceptions.HomeAssistantError):
    """Error to indicate the Durin code is invalid."""


class CodeExpired(exceptions.HomeAssistantError):
    """Error to indicate the Durin code has expired."""