"""
Home Assistant Cloud Integration

This custom component provides cloud-based device synchronization and control
for Home Assistant through AWS services.
"""
import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    API_TIMEOUT,
    SYNC_INTERVAL,
    CONF_API_KEY,
    CONF_API_URL,
    CONF_INSTALLATION_ID,
    CONF_WEBHOOK_URL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.FAN,
    Platform.COVER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Home Assistant Cloud from a config entry."""
    _LOGGER.info("Setting up %s integration", DOMAIN)
    
    # Extract configuration
    config = entry.data
    api_key = config[CONF_API_KEY]
    api_url = config[CONF_API_URL]
    installation_id = config.get(CONF_INSTALLATION_ID)
    webhook_url = config.get(CONF_WEBHOOK_URL)
    
    # Create cloud coordinator
    coordinator = CloudCoordinator(
        hass=hass,
        api_key=api_key,
        api_url=api_url,
        installation_id=installation_id,
        webhook_url=webhook_url,
    )
    
    # Test the connection
    try:
        await coordinator.async_setup()
    except aiohttp.ClientError as err:
        _LOGGER.error("Error connecting to cloud API: %s", err)
        raise ConfigEntryNotReady from err
    except Exception as err:
        _LOGGER.error("Unexpected error setting up cloud coordinator: %s", err)
        raise ConfigEntryNotReady from err
    
    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Set up periodic sync
    async_track_time_interval(
        hass, coordinator.async_sync_devices, SYNC_INTERVAL
    )
    
    _LOGGER.info("Successfully set up %s integration", DOMAIN)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading %s integration", DOMAIN)
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Remove coordinator
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_cleanup()
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class CloudCoordinator:
    """Coordinates communication with the cloud backend."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        api_key: str,
        api_url: str,
        installation_id: str = None,
        webhook_url: str = None,
    ):
        """Initialize the coordinator."""
        self.hass = hass
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.installation_id = installation_id
        self.webhook_url = webhook_url
        self.session = async_get_clientsession(hass)
        self._devices: Dict[str, Any] = {}
        self._entities: Dict[str, Any] = {}
        
    async def async_setup(self) -> None:
        """Set up the coordinator."""
        if not self.installation_id:
            await self._async_register_installation()
        else:
            await self._async_test_connection()
            
        # Initial device sync
        await self.async_sync_devices()
        
    async def async_cleanup(self) -> None:
        """Clean up resources."""
        # Nothing to clean up currently
        pass
        
    async def _async_register_installation(self) -> None:
        """Register this Home Assistant installation with the cloud."""
        _LOGGER.info("Registering installation with cloud backend")
        
        url = f"{self.api_url}/ha/register"
        headers = {"Content-Type": "application/json"}
        data = {"api_key": self.api_key}
        
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with self.session.post(url, headers=headers, json=data) as response:
                    if response.status == 401:
                        raise ConfigEntryAuthFailed("Invalid API key")
                    response.raise_for_status()
                    
                    result = await response.json()
                    self.installation_id = result["installation_id"]
                    self.webhook_url = result["webhook_url"]
                    
                    _LOGGER.info(
                        "Successfully registered installation: %s", 
                        self.installation_id
                    )
                    
        except asyncio.TimeoutError as err:
            raise ConfigEntryNotReady("Timeout connecting to cloud API") from err
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                raise ConfigEntryAuthFailed("Invalid API key") from err
            raise ConfigEntryNotReady(f"HTTP error: {err.status}") from err
            
    async def _async_test_connection(self) -> None:
        """Test connection to the cloud API."""
        _LOGGER.debug("Testing connection to cloud API")
        
        url = f"{self.webhook_url}"
        headers = {"Content-Type": "application/json"}
        data = {"type": "ping"}
        
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with self.session.post(url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    _LOGGER.debug("Cloud API connection test successful")
                    
        except asyncio.TimeoutError as err:
            raise ConfigEntryNotReady("Timeout connecting to cloud API") from err
        except aiohttp.ClientError as err:
            raise ConfigEntryNotReady(f"Connection error: {err}") from err
            
    async def async_sync_devices(self, _now=None) -> None:
        """Sync devices and entities with the cloud."""
        _LOGGER.debug("Syncing devices with cloud backend")
        
        try:
            # Collect all entities from Home Assistant
            devices_data = await self._collect_device_data()
            
            if not devices_data:
                _LOGGER.debug("No devices to sync")
                return
                
            # Send to cloud
            url = f"{self.api_url}/ha/sync"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            data = {
                "installation_id": self.installation_id,
                "devices": devices_data,
            }
            
            async with async_timeout.timeout(API_TIMEOUT):
                async with self.session.post(url, headers=headers, json=data) as response:
                    if response.status == 401:
                        _LOGGER.error("Authentication failed during sync")
                        return
                    response.raise_for_status()
                    
                    result = await response.json()
                    _LOGGER.info(
                        "Synced %d devices, %d entities",
                        result.get("synced_devices", 0),
                        result.get("synced_entities", 0),
                    )
                    
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout during device sync")
        except aiohttp.ClientError as err:
            _LOGGER.warning("Error during device sync: %s", err)
        except Exception as err:
            _LOGGER.exception("Unexpected error during device sync: %s", err)
            
    async def _collect_device_data(self) -> list:
        """Collect device and entity data from Home Assistant."""
        devices = []
        device_registry = await self.hass.helpers.device_registry.async_get_registry()
        entity_registry = await self.hass.helpers.entity_registry.async_get_registry()
        
        # Group entities by device
        device_entities = {}
        
        for entity in entity_registry.entities.values():
            if entity.device_id:
                if entity.device_id not in device_entities:
                    device_entities[entity.device_id] = []
                    
                # Get current state
                state = self.hass.states.get(entity.entity_id)
                if state:
                    entity_data = {
                        "entity_id": entity.entity_id,
                        "name": entity.name or state.name,
                        "device_class": getattr(entity, "device_class", None) or state.attributes.get("device_class"),
                        "state": state.state,
                        "attributes": dict(state.attributes),
                    }
                    device_entities[entity.device_id].append(entity_data)
        
        # Build device data
        for device_id, entities in device_entities.items():
            device_entry = device_registry.async_get(device_id)
            if device_entry:
                device_data = {
                    "device_id": device_id,
                    "name": device_entry.name or "Unknown Device",
                    "manufacturer": device_entry.manufacturer or "Unknown",
                    "model": device_entry.model or "Unknown",
                    "entities": entities,
                }
                devices.append(device_data)
        
        return devices
        
    async def async_send_command(self, entity_id: str, action: str, params: dict = None) -> bool:
        """Send a command to an entity."""
        _LOGGER.debug("Sending command: %s to %s", action, entity_id)
        
        try:
            url = self.webhook_url
            headers = {"Content-Type": "application/json"}
            data = {
                "type": "command",
                "action": action,
                "entity_id": entity_id,
                "params": params or {},
            }
            
            async with async_timeout.timeout(API_TIMEOUT):
                async with self.session.post(url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    return True
                    
        except Exception as err:
            _LOGGER.error("Error sending command: %s", err)
            return False