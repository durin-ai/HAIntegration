"""Constants for the Home Assistant Cloud integration."""
from datetime import timedelta
from typing import Final

# Integration domain
DOMAIN: Final = "your_cloud"

# Configuration keys
CONF_API_KEY: Final = "api_key"
CONF_API_URL: Final = "api_url"
CONF_INSTALLATION_ID: Final = "installation_id"
CONF_WEBHOOK_URL: Final = "webhook_url"

# Default values
DEFAULT_API_URL: Final = "https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/dev"
DEFAULT_NAME: Final = "Home Assistant Cloud"

# Timeouts and intervals
API_TIMEOUT: Final = 30  # seconds
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

# Cloud service endpoints
ENDPOINTS: Final = {
    "register": "/ha/register",
    "sync": "/ha/sync", 
    "webhook": "/webhook",
}

# Service call names
SERVICE_SYNC_DEVICES: Final = "sync_devices"
SERVICE_SEND_COMMAND: Final = "send_command"

# Error messages
ERROR_API_KEY_INVALID: Final = "invalid_api_key"
ERROR_CONNECTION_FAILED: Final = "connection_failed"
ERROR_INSTALLATION_NOT_FOUND: Final = "installation_not_found"
ERROR_SYNC_FAILED: Final = "sync_failed"

# Event types
EVENT_DEVICE_SYNCED: Final = f"{DOMAIN}_device_synced"
EVENT_COMMAND_RECEIVED: Final = f"{DOMAIN}_command_received"
EVENT_STATUS_UPDATE: Final = f"{DOMAIN}_status_update"