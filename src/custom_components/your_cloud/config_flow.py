"""Config flow for Home Assistant Cloud integration."""
import logging
from typing import Any, Dict, Optional

import aiohttp
import async_timeout
import voluptuous as vol
from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_API_URL,
    CONF_API_KEY,
    CONF_API_URL,
    CONF_INSTALLATION_ID,
    CONF_WEBHOOK_URL,
    API_TIMEOUT,
    ERROR_API_KEY_INVALID,
    ERROR_CONNECTION_FAILED,
)

_LOGGER = logging.getLogger(__name__)

# Configuration schema for user input
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_API_KEY): str,
    vol.Optional(CONF_API_URL, default=DEFAULT_API_URL): str,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
})

# Options schema for reconfiguration
OPTIONS_SCHEMA = vol.Schema({
    vol.Optional(CONF_API_URL): str,
})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Assistant Cloud."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    def __init__(self):
        """Initialize the config flow."""
        self._api_key: Optional[str] = None
        self._api_url: Optional[str] = None
        self._name: Optional[str] = None
        self._installation_id: Optional[str] = None
        self._webhook_url: Optional[str] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            self._api_url = user_input[CONF_API_URL].rstrip('/')
            self._name = user_input[CONF_NAME]

            # Validate the API key and register installation
            try:
                await self._test_credentials()
            except InvalidAuth:
                errors["base"] = ERROR_API_KEY_INVALID
            except CannotConnect:
                errors["base"] = ERROR_CONNECTION_FAILED
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during setup")
                errors["base"] = "unknown"
            else:
                # Check if this installation is already configured
                await self.async_set_unique_id(self._installation_id)
                self._abort_if_unique_id_configured()

                # Create the config entry
                return self.async_create_entry(
                    title=self._name,
                    data={
                        CONF_API_KEY: self._api_key,
                        CONF_API_URL: self._api_url,
                        CONF_INSTALLATION_ID: self._installation_id,
                        CONF_WEBHOOK_URL: self._webhook_url,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Dict[str, Any]) -> FlowResult:
        """Handle reauthorization."""
        self._api_url = entry_data.get(CONF_API_URL, DEFAULT_API_URL)
        self._name = entry_data.get(CONF_NAME, DEFAULT_NAME)
        
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Confirm reauthorization."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]

            try:
                await self._test_credentials()
            except InvalidAuth:
                errors["base"] = ERROR_API_KEY_INVALID
            except CannotConnect:
                errors["base"] = ERROR_CONNECTION_FAILED
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
            else:
                # Update the existing entry
                entry = await self.async_set_unique_id(self._installation_id)
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_API_KEY: self._api_key,
                        CONF_INSTALLATION_ID: self._installation_id,
                        CONF_WEBHOOK_URL: self._webhook_url,
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    @core.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def _test_credentials(self) -> None:
        """Validate credentials and register installation."""
        session = async_get_clientsession(self.hass)
        
        # Try to register the installation
        url = f"{self._api_url}/ha/register"
        headers = {"Content-Type": "application/json"}
        data = {"api_key": self._api_key}

        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 401:
                        raise InvalidAuth("Invalid API key")
                    elif response.status >= 400:
                        _LOGGER.error("HTTP error %s: %s", response.status, await response.text())
                        raise CannotConnect(f"HTTP error: {response.status}")
                    
                    response.raise_for_status()
                    result = await response.json()
                    
                    self._installation_id = result["installation_id"]
                    self._webhook_url = result["webhook_url"]
                    
                    _LOGGER.info(
                        "Successfully registered installation: %s", 
                        self._installation_id
                    )

        except aiohttp.ClientConnectorError as err:
            _LOGGER.error("Connection error: %s", err)
            raise CannotConnect("Cannot connect to cloud API") from err
        except aiohttp.ClientResponseError as err:
            _LOGGER.error("HTTP error: %s", err)
            if err.status == 401:
                raise InvalidAuth("Invalid API key") from err
            raise CannotConnect(f"HTTP error: {err.status}") from err
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

        current_api_url = self.config_entry.data.get(CONF_API_URL, DEFAULT_API_URL)
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_API_URL, 
                    default=current_api_url
                ): str,
            }),
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""