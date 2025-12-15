"""Config flow for Home Assistant Cloud integration."""
import logging
from typing import Any, Dict, Optional

import aiomqtt
import async_timeout
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_MQTT_BROKER,
    DEFAULT_MQTT_PORT,
    DEFAULT_USE_TLS,
    CONF_MQTT_BROKER,
    CONF_MQTT_PORT,
    CONF_MQTT_USERNAME,
    CONF_MQTT_PASSWORD,
    CONF_INSTALLATION_ID,
    CONF_USE_TLS,
    MQTT_TIMEOUT,
    ERROR_MQTT_AUTH_FAILED,
    ERROR_MQTT_CONNECTION_FAILED,
)

_LOGGER = logging.getLogger(__name__)

# Configuration schema for user input
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_MQTT_BROKER, default=DEFAULT_MQTT_BROKER): str,
    vol.Optional(CONF_MQTT_PORT, default=DEFAULT_MQTT_PORT): int,
    vol.Required(CONF_MQTT_USERNAME): str,
    vol.Required(CONF_MQTT_PASSWORD): str,
    vol.Optional(CONF_USE_TLS, default=DEFAULT_USE_TLS): bool,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
})

# Options schema for reconfiguration
OPTIONS_SCHEMA = vol.Schema({
    vol.Optional(CONF_MQTT_BROKER): str,
    vol.Optional(CONF_MQTT_PORT): int,
    vol.Optional(CONF_USE_TLS): bool,
})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Assistant Cloud."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self._mqtt_broker: Optional[str] = None
        self._mqtt_port: Optional[int] = None
        self._mqtt_username: Optional[str] = None
        self._mqtt_password: Optional[str] = None
        self._use_tls: Optional[bool] = None
        self._name: Optional[str] = None
        self._installation_id: Optional[str] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._mqtt_broker = user_input[CONF_MQTT_BROKER]
            self._mqtt_port = user_input[CONF_MQTT_PORT]
            self._mqtt_username = user_input[CONF_MQTT_USERNAME]
            self._mqtt_password = user_input[CONF_MQTT_PASSWORD]
            self._use_tls = user_input.get(CONF_USE_TLS, True)
            self._name = user_input[CONF_NAME]

            # Validate MQTT credentials
            try:
                await self._test_mqtt_connection()
            except InvalidAuth:
                errors["base"] = ERROR_MQTT_AUTH_FAILED
            except CannotConnect:
                errors["base"] = ERROR_MQTT_CONNECTION_FAILED
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during setup")
                errors["base"] = "unknown"
            else:
                # Use broker as unique ID to prevent duplicate configurations
                await self.async_set_unique_id(f"{self._mqtt_broker}:{self._mqtt_port}")
                self._abort_if_unique_id_configured()

                # Create the config entry
                return self.async_create_entry(
                    title=self._name,
                    data={
                        CONF_MQTT_BROKER: self._mqtt_broker,
                        CONF_MQTT_PORT: self._mqtt_port,
                        CONF_MQTT_USERNAME: self._mqtt_username,
                        CONF_MQTT_PASSWORD: self._mqtt_password,
                        CONF_USE_TLS: self._use_tls,
                        CONF_NAME: self._name,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Dict[str, Any]) -> FlowResult:
        """Handle reauthorization."""
        self._mqtt_broker = entry_data.get(CONF_MQTT_BROKER, DEFAULT_MQTT_BROKER)
        self._mqtt_port = entry_data.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT)
        self._use_tls = entry_data.get(CONF_USE_TLS, DEFAULT_USE_TLS)
        self._name = entry_data.get(CONF_NAME, DEFAULT_NAME)
        
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Confirm reauthorization."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._mqtt_username = user_input[CONF_MQTT_USERNAME]
            self._mqtt_password = user_input[CONF_MQTT_PASSWORD]

            try:
                await self._test_mqtt_connection()
            except InvalidAuth:
                errors["base"] = ERROR_MQTT_AUTH_FAILED
            except CannotConnect:
                errors["base"] = ERROR_MQTT_CONNECTION_FAILED
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                # Update the existing entry
                entry = await self.async_set_unique_id(
                    f"{self._mqtt_broker}:{self._mqtt_port}"
                )
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_MQTT_USERNAME: self._mqtt_username,
                        CONF_MQTT_PASSWORD: self._mqtt_password,
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({
                vol.Required(CONF_MQTT_USERNAME): str,
                vol.Required(CONF_MQTT_PASSWORD): str,
            }),
            errors=errors,
        )

    @staticmethod
    @core.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def _test_mqtt_connection(self) -> None:
        """Validate MQTT credentials by attempting to connect."""
        _LOGGER.debug("Testing MQTT connection to %s:%d", self._mqtt_broker, self._mqtt_port)
        
        try:
            async with async_timeout.timeout(MQTT_TIMEOUT):
                client = aiomqtt.Client(
                    hostname=self._mqtt_broker,
                    port=self._mqtt_port,
                    username=self._mqtt_username,
                    password=self._mqtt_password,
                    keepalive=60,
                    tls_context=None if not self._use_tls else True,
                )
                
                async with client:
                    # Connection successful
                    _LOGGER.info("MQTT connection test successful")
                    
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout connecting to MQTT broker")
            raise CannotConnect("Timeout connecting to MQTT broker") from err
        except aiomqtt.MqttError as err:
            _LOGGER.error("MQTT error: %s", err)
            if "authentication" in str(err).lower() or "unauthorized" in str(err).lower():
                raise InvalidAuth("MQTT authentication failed") from err
            raise CannotConnect(f"MQTT connection error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            raise CannotConnect("Unexpected error") from err


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_broker = self.config_entry.data.get(CONF_MQTT_BROKER, DEFAULT_MQTT_BROKER)
        current_port = self.config_entry.data.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT)
        current_use_tls = self.config_entry.data.get(CONF_USE_TLS, DEFAULT_USE_TLS)
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_MQTT_BROKER, 
                    default=current_broker
                ): str,
                vol.Optional(
                    CONF_MQTT_PORT,
                    default=current_port
                ): int,
                vol.Optional(
                    CONF_USE_TLS,
                    default=current_use_tls
                ): bool,
            }),
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""