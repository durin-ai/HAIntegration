from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.network import get_url
from pathlib import Path
import json

import argparse
from awsiot import mqtt_connection_builder
from awscrt import mqtt
from awsiot import iotshadow
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import time
import asyncio
from ulid import ULID
import secrets
import random
import logging
import base64
import aiohttp

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar


DOMAIN = "ha_durin_integration"
BASE_PATH = Path(__file__).parent
_LOGGER = logging.getLogger(__name__)

subscription_topics = [
    "$aws/provisioning-templates/AiDurinIOT_FleetProvisioningTemplate/provision/json/accepted",
    "$aws/provisioning-templates/AiDurinIOT_FleetProvisioningTemplate/provision/json/rejected",
    "$aws/certificates/create/json/accepted",
    "$aws/certificates/create/json/rejected"
]

def random_mac() -> str:
    b = secrets.token_bytes(6)

    # format as "AA:BB:CC:DD:EE:FF"
    return ":".join(f"{byte:02X}" for byte in b)

class DurinIoT:
    keyPath: str = str(BASE_PATH / "data" / "claim-cert.key")
    certPath: str =  str(BASE_PATH / "data" / "claim-cert.pem")
    caPath: str =  str(BASE_PATH / "data" / "combined.pem")
    clientId: str = '0000-clientid-0000'
    iot_host: str = 'a3nslargir2uhb-ats.iot.us-east-2.amazonaws.com'
    iot_protocol: str = 'mqtts'
    pending_futures: dict[str, asyncio.Future[str]] = {}

    def __init__(self, entity_code, hass: HomeAssistant, entry: ConfigEntry):
        self.entityId = entity_code
        self.hass = hass
        self.entry = entry
        self.LOOP: asyncio.AbstractEventLoop = hass.loop

    def PublishTopic(self, topic, payload={}):
        self.mqtt_connection.publish(
        topic=f"{topic}",
        payload=json.dumps(payload).encode("utf-8"),  # bytes
        qos=mqtt.QoS.AT_MOST_ONCE,
        )

    def SubscribeTopic(self, topic):
        self.mqtt_connection.subscribe(
            topic=f"{topic}",
            qos=mqtt.QoS.AT_MOST_ONCE,
            callback=self.on_message_received
        )

    async def SendCloudCommand(self, command, body):
        command_id = f"IOT.CLDOP~{ULID()}"
        body = {"method": f"{command}",
                "response": f"$aws/things/{self.thingName}/commands/status/{command_id}",
                "body": body}
        fut = self.LOOP.create_future()
        self.pending_futures[command_id] = fut

        self.PublishTopic(f"$aws/things/{self.thingName}/commands/request/{command_id}", body)
        try:
            return await asyncio.wait_for(fut, timeout=20)
        except asyncio.TimeoutError:
            self.pending_futures.pop(command_id, None)
            return None
        

    # Define event handlers
    def on_connection_interrupted(self, connection, error, **kwargs):
        _LOGGER.warning("Connection interrupted. error: %s", error)
    def on_connection_resumed(self, connection, return_code, session_present, **kwargs):
        _LOGGER.warning("Connection resumed. return_code: %s session_present: %s", return_code, session_present)

    def on_message_received(self, topic, payload, dup, qos, retain, **kwargs):
        self.LOOP.call_soon_threadsafe(self.hass.async_create_task, self.on_message_received_safe(topic, payload))
    
    async def on_message_received_safe(self, topic:str, payload):
        match topic:
            case "$aws/certificates/create/json/accepted":
                _LOGGER.warning("Device Certificate Created")
                payload = json.loads(payload.decode("utf-8"))
                payload = {
                    **payload,
                    "SerialNumber": f"{ULID()}",
                    "DeviceType": "HAIntegration",
                    "EntityId": f"{self.entityId}",
                    "MAC_ADDRESS": f"{random_mac()}"
                }

                registerPayload = {
                    "certificateOwnershipToken": f"{payload['certificateOwnershipToken']}",
                    "parameters": {
                        "SerialNumber": f"{payload['SerialNumber']}",
                        "DeviceType": f"{payload['DeviceType']}",
                        "EntityId": f"{payload['EntityId']}",
                        "MAC_ADDRESS": f"{payload['MAC_ADDRESS']}",
                    }
                }

                del payload['certificateOwnershipToken']
                persisted_data = {**self.entry.data}
                persisted_data["thing_data"] = payload
                self.hass.config_entries.async_update_entry(self.entry, data=persisted_data)
                self.PublishTopic(topic="$aws/provisioning-templates/AiDurinIOT_FleetProvisioningTemplate/provision/json", payload=registerPayload)

            case "$aws/certificates/create/json/rejected":
                _LOGGER.warning("Device Certificate Rejected")
            case "$aws/provisioning-templates/AiDurinIOT_FleetProvisioningTemplate/provision/json/accepted":
                payload = json.loads(payload.decode('utf-8'))
                _LOGGER.warning(f"Thing Name => {payload['thingName']}")

                persisted_data = {**self.entry.data}
                persisted_data["thing_data"] = {**persisted_data["thing_data"], "thingName": payload['thingName']}
                self.hass.config_entries.async_update_entry(self.entry, data=persisted_data)
                
                _LOGGER.warning("Provisioning [%s] COMPLETE, disconnecting provisioning connection...",  payload['thingName'])
                await self.on_device_provisioning_complete_safe(self.mqtt_connection)
            case _:
                if topic.startswith(f"$aws/things/{self.thingName}/commands/request/IOT.CMD~"):
                    payload = json.loads(payload.decode('utf-8'))
                    _LOGGER.warning("Message received on topic '%s': %s",  topic, payload)
                    if payload['method'] == "executeCapabilityOperation" and payload['body']['capabilityId'].startswith("CAP.HAINT~"):
                        await self.on_iot_command_received(payload['body']['operationId'], payload['response'], { k: v for k, v in payload["body"].items() if k not in {"operationId"}})
                elif topic.startswith(f"$aws/things/{self.thingName}/commands/status/IOT.CLDOP~"):
                    command_id = topic.rsplit("/", 1)[-1]
                    fut = self.pending_futures.pop(command_id, None)
                    if fut and not fut.done():
                        payload = json.loads(payload.decode('utf-8'))
                        fut.set_result({"status": payload.get("status", None), "result": payload.get("result", None)})
                elif topic.startswith(f"$aws/things/{self.thingName}/commands/request/IOT.CLDOP~"):
                    # No Op, because this is our own message
                    pass
                else:
                    _LOGGER.warning("Message received on topic '%s': %s",  topic, payload.decode('utf-8'))

    async def on_device_provisioning_complete_safe(self, connection):
        await asyncio.wrap_future(connection.disconnect())
        self.StartDevice()

    def on_connect_handler(self, connection, callback_data):
        self.LOOP.call_soon_threadsafe(self.hass.async_create_task, self.on_connect_handler_safe(connection, callback_data))

    async def on_connect_handler_safe(self, connection, callback_data):
        for topic in subscription_topics:
            subscribe_future, packet_id = self.mqtt_connection.subscribe(
                topic=f"{topic}",
                qos=mqtt.QoS.AT_MOST_ONCE,
                callback=self.on_message_received)
            await asyncio.wrap_future(subscribe_future)
        self.PublishTopic(topic="$aws/certificates/create/json")

    def FleetProvision(self):
        # Build connection
        self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=self.iot_host,
            cert_filepath=self.certPath,
            pri_key_filepath=self.keyPath,
            ca_filepath=self.caPath,
            client_id=self.clientId,
            clean_session=True,
            keep_alive_secs=30,
            on_connection_success=self.on_connect_handler
        )
        self.mqtt_connection.connect()

    def on_shadow_get_accepted(self, response):
        self.LOOP.call_soon_threadsafe(self.hass.async_create_task, self.on_shadow_get_accepted_safe(response.state.reported))
    async def on_shadow_get_accepted_safe(self, reported):
        # Full shadow document is here
        _LOGGER.warning("Shadow state: %s", reported)
        self.remove_event_sub = self.hass.bus.async_listen(EVENT_STATE_CHANGED, self.on_ha_event)

    def on_ha_event(self, event):
        try:
            entity_id = event.data["entity_id"]
            old_state = event.data["old_state"]
            new_state = event.data["new_state"]

            self.LOOP.call_soon_threadsafe(self.hass.async_create_task, self.on_ha_event_safe(entity_id, old_state, new_state))
        except KeyError:
            pass
    
    async def on_ha_event_safe(self, entity_id, old_state, new_state):
        diff_keys = [k for k in (old_state.attributes.keys() & new_state.attributes.keys()) if old_state.attributes[k] != new_state.attributes[k]]
        diff_dict = {k: (old_state.attributes[k], new_state.attributes[k]) for k in diff_keys}
        _LOGGER.warning("State Change on: %s => %s to %s [%s]", 
                        entity_id, 
                        old_state.state if old_state is not None else "unknown", 
                        new_state.state if new_state is not None else "unknown",
                        diff_dict)
        
        # Check if this entity is mapped to durin
        mapped_entities = set(self.entry.options.get("mapped_entities", []))

        if entity_id in mapped_entities:
            await self.SendCloudCommand("home-assistant-update", {"state_change": {"entity_id": entity_id, "old_state": old_state.state if old_state is not None else "unknown", "new_state": new_state.state if new_state is not None else "unknown", "changed_attributes": diff_dict}})


        #if not entity_id.startswith('sun.'):
        #    results = await self.SendCloudCommand("home-assistant-update", {"state_change": {"entity_id": entity_id, "old_state": old_state.state if old_state is not None else "unknown", "new_state": new_state.state if new_state is not None else "unknown", "changed_attributes": diff_dict}})
        #    _LOGGER.warning(results)
        #else:
        #     _LOGGER.warning(f"Skipping updating cloud for: {entity_id}")


    def on_shadow_get_rejected(self, error):
        self.shadow_retry_count += 1
        self.LOOP.call_soon_threadsafe(self.hass.async_create_task, self.on_shadow_get_rejected_safe(error.message))
    async def on_shadow_get_rejected_safe(self, message):
        delay = min(2 ** self.shadow_retry_count, 180)  # Cap at 3 minutes
        delay += random.uniform(1.0, 3.0)               # Add random jitter

        _LOGGER.warning(f"Retrying in {delay} seconds...")
        await asyncio.sleep(delay)
        self.shadow_client.publish_get_shadow(
            request=iotshadow.GetShadowRequest(thing_name=self.thingName),
            qos=mqtt.QoS.AT_LEAST_ONCE)


    def on_device_connect_handler(self, connection, callback_data):
        self.LOOP.call_soon_threadsafe(self.hass.async_create_task, self.on_device_connect_handler_safe(connection, callback_data))
    async def on_device_connect_handler_safe(self, connection, callback_data):
        self.SubscribeTopic(f"$aws/things/{self.thingName}/jobs/notify")
        self.SubscribeTopic(f"$aws/things/{self.thingName}/commands/request/#")
        self.SubscribeTopic(f"$aws/things/{self.thingName}/commands/status/#")
        self.SubscribeTopic(f"$aws/things/{self.thingName}/certificate/renew/json/accepted")
        self.shadow_client = iotshadow.IotShadowClient(self.mqtt_connection)
        self.shadow_retry_count = 0

        get_accepted_subscribed_future, _ = self.shadow_client.subscribe_to_get_shadow_accepted(
            request=iotshadow.GetShadowSubscriptionRequest(thing_name=self.thingName),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_shadow_get_accepted)
        get_rejected_subscribed_future, _ = self.shadow_client.subscribe_to_get_shadow_rejected(
            request=iotshadow.GetShadowSubscriptionRequest(thing_name=self.thingName),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self.on_shadow_get_rejected)
        
        await asyncio.wrap_future(get_accepted_subscribed_future)
        await asyncio.wrap_future(get_rejected_subscribed_future)
        
        self.shadow_client.publish_get_shadow(
            request=iotshadow.GetShadowRequest(thing_name=self.thingName),
            qos=mqtt.QoS.AT_LEAST_ONCE)
        
    def StartDevice(self):
        self.thingName = self.entry.data["thing_data"]["thingName"]
        self.mqtt_connection = mqtt_connection_builder.mtls_from_bytes(
            endpoint=self.iot_host,
            cert_bytes=self.entry.data["thing_data"]['certificatePem'].encode('utf-8'),
            pri_key_bytes=self.entry.data["thing_data"]['privateKey'].encode('utf-8'),
            ca_filepath=self.caPath,
            client_id=self.entry.data["thing_data"]['thingName'],
            clean_session=True,
            keep_alive_secs=30,
            on_connection_success=self.on_device_connect_handler
        )

        self.mqtt_connection.connect()
    def Start(self):
        try:
            payload = self.entry.data["thing_data"]
        except KeyError:
            self.FleetProvision()
            return

        _LOGGER.warning(payload)
        self.thingName = payload['thingName']
        if not self.entry.options:
            self.hass.config_entries.async_update_entry(
                self.entry,
                options={ 
                    "thing_name": self.thingName
                }
            )

        self.mqtt_connection = mqtt_connection_builder.mtls_from_bytes(
            endpoint=self.iot_host,
            cert_bytes=payload['certificatePem'].encode('utf-8'),
            pri_key_bytes=payload['privateKey'].encode('utf-8'),
            ca_filepath=self.caPath,
            client_id=payload['thingName'],
            clean_session=True,
            keep_alive_secs=30,
            on_connection_success=self.on_device_connect_handler
        )
        self.mqtt_connection.connect()
    
    async def device_representation(self, dev, device_table, top_level_only):
        entity_registry = er.async_get(self.hass)
        area_registry = ar.async_get(self.hass)

        entity_entries = [
            ent
            for ent in entity_registry.entities.values()
            if ent.device_id == dev.id
        ]
        names = [
            self.hass.states.get(ent.entity_id).attributes.get("friendly_name", None)
            for ent in entity_entries
            if (state := self.hass.states.get(ent.entity_id)) is not None
            and state.attributes.get("friendly_name", None) is not None 
            and state.attributes.get("device_class", None) not in ("identify", "firmware")
            and dev.via_device_id is None
        ]

        return {
            "area": (
                area_registry.async_get_area(dev.area_id).name
                if dev.area_id is not None and area_registry.async_get_area(dev.area_id) is not None
                else None
            ),
            "id": dev.id,
            "parent_id": dev.via_device_id,
            "name": min(names, key=len, default=dev.name or dev.name_by_user) if (dev.name or dev.name_by_user)==dev.model else (dev.name or dev.name_by_user),
            "manufacturer": dev.manufacturer,
            "model": dev.model,
            "identifiers": list(dev.identifiers),
            "entities": [
                {
                    "entity_id": ent.entity_id,
                    "domain": ent.domain,
                    "platform": ent.platform,
                    "disabled_by": ent.disabled_by,
                    **(
                        {
                            "friendly_name": (
                                (state := self.hass.states.get(ent.entity_id)).attributes.get("friendly_name")
                                if state is not None
                                else None
                            )
                        }
                        if (state := self.hass.states.get(ent.entity_id)) is not None
                        else {}
                    ),
                }
                for ent in entity_entries
                if not top_level_only
            ],
            "devices": [
                await self.device_representation(dv, device_table, top_level_only)
                for i, (k, dv) in enumerate(device_table.items())
                if dv.via_device_id == dev.id
                and not top_level_only
            ]
        }


    async def on_iot_command_received(self, operationId, responseTopic, body):
        _LOGGER.warning(f"IOT_COMMAND_RECEIVED: {operationId} => {responseTopic} [%s]", body)
        
        # This is called on the HA Event Loop Thread

        match operationId:
            case "get_url":
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": get_url(self.hass)})

            case "restart_home_assistant":
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": "pending"})
                await self.hass.services.async_call(
                    "homeassistant",
                    "restart",
                    {},
                    blocking=False
                )

            case "update_integration":
                session: aiohttp.ClientSession = async_get_clientsession(self.hass)
                integration_path =  str(BASE_PATH / "__init__.py")
                update_path = body.get('update_path', None)

                if update_path is not None:
                    async with session.get(update_path) as resp:
                            resp.raise_for_status()
                            update_string = await resp.text()

                    try:
                        with open(integration_path, "w", encoding="utf-8") as f:
                            f.write(update_string)
                    except Exception as e:
                        self.PublishTopic(topic=responseTopic, payload={"status": "FAILED", "result": f"Write Failed: {e}"})
                        return

                    self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": "RESTARTING"})
                    await self.hass.services.async_call(
                        "homeassistant",
                        "restart",
                        {},
                        blocking=False
                    )


            case "list_entities":
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": [s.entity_id for s in self.hass.states.async_all(body.get("domain", None))]})

            case "list_domains":
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": list({state.domain for state in self.hass.states.async_all()})})

            case "list_areas":
                entity_registry = er.async_get(self.hass)
                area_registry = ar.async_get(self.hass)
                device_registry = dr.async_get(self.hass)

                area_id = body.get('area_id', None)

                result = [
                    {
                        "id": area.id,
                        "name": area.name,
                        "entities": [
                            ent.entity_id
                            for ent in entity_registry.entities.values()
                            if ent is not None
                            and (
                                ent.area_id == area.id
                                or (
                                    ent.area_id is None
                                    and ent.device_id is not None
                                    and (
                                        (dev := device_registry.devices.get(ent.device_id)) is not None
                                        and dev.area_id == area.id
                                    )
                                )
                            )
                            and area_id is not None
                        ]
                    }
                    for area in list(area_registry.async_list_areas())
                    if area_id is None 
                    or area_id == area.id
                ]
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": result})

            case "get_state":
                entity_id = body.get('entity_id', [])
                if not isinstance(entity_id, (list)):
                    entity_id = [entity_id]

                result = {
                    f"{id}": state.as_dict()
                    for id in entity_id
                    if (state := self.hass.states.get(id)) is not None
                    and hasattr(state, "as_dict")
                }
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": result})

            case "list_integrations":
                domain_filter = body.get('domain', None)
                self.PublishTopic(
                    topic=responseTopic, 
                    payload={
                        "status": "COMPLETE", 
                        "result": [
                            {
                                "entry_id": s.entry_id,
                                "domain": s.domain,
                                "title": s.title,
                                "source": s.source,
                                "state": s.state.value,  # enum -> string
                                "disabled_by": s.disabled_by
                            } 
                            for s in self.hass.config_entries.async_entries() 
                            if s.disabled_by is None
                            and (domain_filter is None or s.domain == domain_filter)
                        ]
                    }
                )

            case "get_integration_devices":
                entry_id = body.get('entry_id', None)
                device_id = body.get('device_id', None)
                device_registry = dr.async_get(self.hass)
                entity_registry = er.async_get(self.hass)
                area_registry = ar.async_get(self.hass)

                device_table = {
                    dev.id: dev
                    for dev in device_registry.devices.values()
                    if entry_id in dev.config_entries
                }

                top_level_devices = [
                    dev
                    for i, (dev_id, dev) in enumerate(device_table.items())
                    if dev.via_device_id is None
                    and (device_id is None or device_id == dev.id)
                ]

                result = [
                    await self.device_representation(dv, device_table, device_id is None)
                    for dv in top_level_devices
                ]
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": result})
                

            case "list_device_mapped_entities":
                entry_id = body.get('entry_id', None)
                device_id = body.get('device_id', None)
                device_registry = dr.async_get(self.hass)
                entity_registry = er.async_get(self.hass)

                device_ids = {
                    dev.id
                    for dev in device_registry.devices.values()
                    if entry_id in dev.config_entries
                    and (device_id is None or dev.id == device_id)
                }

                result = [
                    ent.entity_id
                    for ent in entity_registry.entities.values()
                    if ent.device_id in device_ids
                    and (device_id is None or ent.device_id == device_id)
                ]

                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": result})

            case "remove_area_mapped_entities":
                area_id = body.get('area_id', None)
                device_registry = dr.async_get(self.hass)
                entity_registry = er.async_get(self.hass)
                area_registry = ar.async_get(self.hass)

                entity_ids = [
                    ent.entity_id
                    for ent in entity_registry.entities.values()
                    if ent is not None
                    and (
                        ent.area_id == area_id
                        or (
                            ent.area_id is None
                            and ent.device_id is not None
                            and (
                                (dev := device_registry.devices.get(ent.device_id)) is not None
                                and dev.area_id == area_id
                            )
                        )
                    ) 
                ]

                mapped_entities = set(self.entry.options.get("mapped_entities", []))
                mapped_entities.difference_update(entity_ids)

                new_options = {
                    **self.entry.options,
                    "mapped_entities": list(mapped_entities)
                }
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    options=new_options,
                )
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": entity_ids})


            case "remove_device_mapped_entities":
                entry_id = body.get('entry_id', None)
                device_id = body.get('device_id', None)
                device_registry = dr.async_get(self.hass)
                entity_registry = er.async_get(self.hass)

                device_ids = {
                    dev.id
                    for dev in device_registry.devices.values()
                    if entry_id in dev.config_entries
                    and (device_id is None or dev.id == device_id)
                }

                result = [
                    ent.entity_id
                    for ent in entity_registry.entities.values()
                    if ent.device_id in device_ids
                    and (device_id is None or ent.device_id == device_id)
                ]

                mapped_entities = set(self.entry.options.get("mapped_entities", []))
                mapped_entities.difference_update(result)

                new_options = {
                    **self.entry.options,
                    "mapped_entities": list(mapped_entities)
                }
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    options=new_options,
                )

                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": result})

            case "forwarded_entities_list":
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": self.entry.options.get("mapped_entities", [])})

            case "forwarded_entities_add":
                mapped_entities = set(self.entry.options.get("mapped_entities", []))
                mapped_entities.update(body.get('unmapped_entities', []))

                new_options = {
                    **self.entry.options,
                    "mapped_entities": list(mapped_entities)
                }
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    options=new_options,
                )
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": body.get('unmapped_entities', [])})
            
            case "forwarded_entities_delete":
                mapped_entities = set(self.entry.options.get("mapped_entities", []))
                mapped_entities.difference_update(body.get('mapped_entities', []))

                new_options = {
                    **self.entry.options,
                    "mapped_entities": list(mapped_entities)
                }
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    options=new_options,
                )
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": body.get('mapped_entities', [])})

            case "device_delete_forwarded_entities":
                entry_id = body.get('entry_id', None)
                device_id = body.get('device_id', None)
                device_registry = dr.async_get(self.hass)
                entity_registry = er.async_get(self.hass)
                
                mapped_entities = set(self.entry.options.get("mapped_entities", []))
                mapped_entities.difference_update(
                    [
                        ent.entity_id
                        for dev in device_registry.devices.values()
                        if entry_id in dev.config_entries
                        and (device_id is None or dev.id == device_id)
                        for ent in entity_registry.entities.values()
                        if ent.device_id == dev.id
                    ]
                )
                new_options = {
                    **self.entry.options,
                    "mapped_entities": list(mapped_entities)
                }
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    options=new_options,
                )
                self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE", "result": "OK"})

            case "invoke_command":
                if {"command", "domain", "payload"} <= body.keys():
                    await self.hass.services.async_call(body['domain'], body['command'], body['payload'])
                    self.PublishTopic(topic=responseTopic, payload={"status": "COMPLETE"})
                else:
                    self.PublishTopic(topic=responseTopic, payload={"status": "FAILED"})




async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up your integration from a config entry."""
    # Store any shared client or state in hass.data
    hass.data.setdefault(DOMAIN, {})

    durin_instance = DurinIoT(entry.data.get("residence_code"), hass, entry)
    durin_instance.Start()

    hass.data[DOMAIN][entry.entry_id] = { "durin": durin_instance }
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
