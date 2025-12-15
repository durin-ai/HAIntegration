"""Constants for the Durin Ecosystem integration."""
from datetime import timedelta
from typing import Final

# Integration domain
DOMAIN: Final = "durin"

# Configuration keys
CONF_API_KEY: Final = "api_key"
CONF_MQTT_BROKER: Final = "mqtt_broker"
CONF_MQTT_PORT: Final = "mqtt_port"
CONF_MQTT_USERNAME: Final = "mqtt_username"
CONF_MQTT_PASSWORD: Final = "mqtt_password"
CONF_INSTALLATION_ID: Final = "installation_id"
CONF_USE_TLS: Final = "use_tls"

# Default values
DEFAULT_MQTT_BROKER: Final = "your-iot-endpoint.iot.us-east-1.amazonaws.com"
DEFAULT_MQTT_PORT: Final = 8883  # MQTT over TLS
DEFAULT_NAME: Final = "Durin Ecosystem"
DEFAULT_USE_TLS: Final = True

# Timeouts and intervals
MQTT_TIMEOUT: Final = 30  # seconds
MQTT_KEEPALIVE: Final = 60  # seconds
SYNC_INTERVAL: Final = timedelta(minutes=5)  # Sync every 5 minutes
RETRY_INTERVAL: Final = timedelta(minutes=1)  # Retry failed operations after 1 minute

# Supported device types that can be synced
SUPPORTED_DOMAINS: Final = [
    "light",
    "switch",
    "sensor", 
    "binary_sensor",
    "climate",
    "fan",
    "cover",
    "lock",
    "alarm_control_panel",
    "camera",
    "media_player",
    "vacuum",
]

# Entity attributes to exclude from sync (privacy/size optimization)
EXCLUDED_ATTRIBUTES: Final = [
    "context",
    "last_changed",
    "last_updated",
    "entity_picture",
    "icon",
    "assumed_state",
]

# Device classes that should trigger security alerts
SECURITY_DEVICE_CLASSES: Final = [
    "door",
    "garage_door", 
    "lock",
    "opening",
    "window",
    "motion",
    "occupancy",
    "presence",
    "smoke",
    "gas",
    "safety",
    "tamper",
]

# Maximum number of entities to sync in one batch
MAX_SYNC_ENTITIES: Final = 100

# MQTT topics
MQTT_TOPICS: Final = {
    "register": "durin/ha/{installation_id}/register",
    "sync": "durin/ha/{installation_id}/sync",
    "commands": "durin/ha/{installation_id}/commands",
    "status": "durin/ha/{installation_id}/status",
    "events": "durin/ha/{installation_id}/events",
}

# Service call names
SERVICE_SYNC_DEVICES: Final = "sync_devices"
SERVICE_SEND_COMMAND: Final = "send_command"

# Error messages
ERROR_MQTT_AUTH_FAILED: Final = "mqtt_auth_failed"
ERROR_MQTT_CONNECTION_FAILED: Final = "mqtt_connection_failed"
ERROR_BROKER_UNREACHABLE: Final = "broker_unreachable"
ERROR_SYNC_FAILED: Final = "sync_failed"

# Event types
EVENT_DEVICE_SYNCED: Final = f"{DOMAIN}_device_synced"
EVENT_COMMAND_RECEIVED: Final = f"{DOMAIN}_command_received"
EVENT_STATUS_UPDATE: Final = f"{DOMAIN}_status_update"