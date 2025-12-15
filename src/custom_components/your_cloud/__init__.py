"""
Home Assistant Cloud Integration

This custom component provides cloud-based device synchronization and control
for Home Assistant through AWS IoT Core using MQTT.
"""
import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Dict
import uuid

import aiomqtt
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    MQTT_TIMEOUT,
    MQTT_KEEPALIVE,
    SYNC_INTERVAL,
    CONF_MQTT_BROKER,
    CONF_MQTT_PORT,
    CONF_MQTT_USERNAME,
    CONF_MQTT_PASSWORD,
    CONF_INSTALLATION_ID,
    CONF_USE_TLS,
    MQTT_TOPICS,
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
    mqtt_broker = config[CONF_MQTT_BROKER]
    mqtt_port = config[CONF_MQTT_PORT]
    mqtt_username = config.get(CONF_MQTT_USERNAME)
    mqtt_password = config.get(CONF_MQTT_PASSWORD)
    installation_id = config.get(CONF_INSTALLATION_ID)
    use_tls = config.get(CONF_USE_TLS, True)
    
    # Generate installation ID if not present
    if not installation_id:
        installation_id = str(uuid.uuid4())
        hass.config_entries.async_update_entry(
            entry, data={**config, CONF_INSTALLATION_ID: installation_id}
        )
    
    # Create MQTT coordinator
    coordinator = MQTTCoordinator(
        hass=hass,
        broker=mqtt_broker,
        port=mqtt_port,
        username=mqtt_username,
        password=mqtt_password,
        installation_id=installation_id,
        use_tls=use_tls,
    )
    
    # Test the connection
    try:
        await coordinator.async_setup()
    except aiomqtt.MqttError as err:
        _LOGGER.error("Error connecting to MQTT broker: %s", err)
        raise ConfigEntryNotReady from err
    except Exception as err:
        _LOGGER.error("Unexpected error setting up MQTT coordinator: %s", err)
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


class MQTTCoordinator:
    """Coordinates communication with the cloud backend via MQTT."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        broker: str,
        port: int,
        username: str,
        password: str,
        installation_id: str,
        use_tls: bool = True,
    ):
        """Initialize the coordinator."""
        self.hass = hass
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.installation_id = installation_id
        self.use_tls = use_tls
        self._client = None
        self._devices: Dict[str, Any] = {}
        self._entities: Dict[str, Any] = {}
        self._listening_task = None
        
    async def async_setup(self) -> None:
        """Set up the coordinator."""
        await self._async_connect()
        
        # Start listening for commands
        self._listening_task = asyncio.create_task(self._async_listen_for_commands())
        
        # Publish registration message
        await self._async_register_installation()
        
        # Initial device sync
        await self.async_sync_devices()
        
    async def async_cleanup(self) -> None:
        """Clean up resources."""
        if self._listening_task:
            self._listening_task.cancel()
            try:
                await self._listening_task
            except asyncio.CancelledError:
                pass
        
        if self._client:
            await self._client.disconnect()
            
    async def _async_connect(self) -> None:
        """Connect to MQTT broker."""
        _LOGGER.info("Connecting to MQTT broker: %s:%d", self.broker, self.port)
        
        try:
            self._client = aiomqtt.Client(
                hostname=self.broker,
                port=self.port,
                username=self.username,
                password=self.password,
                keepalive=MQTT_KEEPALIVE,
                tls_context=None if not self.use_tls else True,
            )
            await self._client.__aenter__()
            _LOGGER.info("Successfully connected to MQTT broker")
            
        except Exception as err:
            _LOGGER.error("Failed to connect to MQTT broker: %s", err)
            raise ConfigEntryNotReady(f"MQTT connection failed: {err}") from err
            
    async def _async_register_installation(self) -> None:
        """Register this Home Assistant installation with the cloud."""
        _LOGGER.info("Registering installation via MQTT")
        
        topic = MQTT_TOPICS["register"].format(installation_id=self.installation_id)
        payload = {
            "installation_id": self.installation_id,
            "timestamp": asyncio.get_event_loop().time(),
        }
        
        try:
            await self._client.publish(topic, json.dumps(payload), qos=1)
            _LOGGER.info("Successfully registered installation: %s", self.installation_id)
        except Exception as err:
            _LOGGER.error("Failed to register installation: %s", err)
            raise
            
    async def async_sync_devices(self, _now=None) -> None:
        """Sync devices and entities with the cloud via MQTT."""
        _LOGGER.debug("Syncing devices via MQTT")
        
        try:
            # Collect all entities from Home Assistant
            devices_data = await self._collect_device_data()
            
            if not devices_data:
                _LOGGER.debug("No devices to sync")
                return
                
            # Publish to MQTT sync topic
            topic = MQTT_TOPICS["sync"].format(installation_id=self.installation_id)
            payload = {
                "installation_id": self.installation_id,
                "devices": devices_data,
                "timestamp": asyncio.get_event_loop().time(),
            }
            
            await self._client.publish(topic, json.dumps(payload), qos=1)
            
            _LOGGER.info(
                "Synced %d devices with %d total entities",
                len(devices_data),
                sum(len(d.get("entities", [])) for d in devices_data),
            )
                    
        except Exception as err:
            _LOGGER.exception("Unexpected error during device sync: %s", err)
            
    async def _async_listen_for_commands(self) -> None:
        """Listen for commands from the cloud via MQTT."""
        commands_topic = MQTT_TOPICS["commands"].format(
            installation_id=self.installation_id
        )
        
        try:
            await self._client.subscribe(commands_topic)
            _LOGGER.info("Subscribed to commands topic: %s", commands_topic)
            
            async for message in self._client.messages:
                try:
                    payload = json.loads(message.payload.decode())
                    await self._process_command(payload)
                except json.JSONDecodeError:
                    _LOGGER.error("Invalid JSON in MQTT message")
                except Exception as err:
                    _LOGGER.error("Error processing command: %s", err)
                    
        except asyncio.CancelledError:
            _LOGGER.debug("Command listener cancelled")
            raise
        except Exception as err:
            _LOGGER.error("Error in command listener: %s", err)
            
    async def _process_command(self, payload: dict) -> None:
        """Process a command received via MQTT."""
        action = payload.get("action")
        entity_id = payload.get("entity_id")
        params = payload.get("params", {})
        
        if not action or not entity_id:
            _LOGGER.warning("Invalid command payload: %s", payload)
            return
            
        _LOGGER.info("Processing command: %s on %s", action, entity_id)
        
        # Execute the command on the local entity
        domain = entity_id.split(".")[0]
        
        try:
            await self.hass.services.async_call(
                domain,
                action,
                {"entity_id": entity_id, **params},
                blocking=True,
            )
            _LOGGER.info("Command executed successfully")
            
            # Publish status update
            await self._async_publish_status_update(entity_id)
            
        except Exception as err:
            _LOGGER.error("Error executing command: %s", err)
            
    async def _async_publish_status_update(self, entity_id: str) -> None:
        """Publish status update for an entity."""
        state = self.hass.states.get(entity_id)
        if not state:
            return
            
        status_topic = MQTT_TOPICS["status"].format(
            installation_id=self.installation_id
        )
        
        payload = {
            "entity_id": entity_id,
            "state": state.state,
            "attributes": dict(state.attributes),
            "timestamp": asyncio.get_event_loop().time(),
        }
        
        try:
            await self._client.publish(status_topic, json.dumps(payload), qos=0)
        except Exception as err:
            _LOGGER.error("Error publishing status update: %s", err)
            
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
        """Send a command to an entity via MQTT."""
        _LOGGER.debug("Publishing command: %s to %s", action, entity_id)
        
        try:
            commands_topic = MQTT_TOPICS["commands"].format(
                installation_id=self.installation_id
            )
            
            payload = {
                "type": "command",
                "action": action,
                "entity_id": entity_id,
                "params": params or {},
                "timestamp": asyncio.get_event_loop().time(),
            }
            
            await self._client.publish(commands_topic, json.dumps(payload), qos=1)
            return True
                    
        except Exception as err:
            _LOGGER.error("Error sending command: %s", err)
            return False