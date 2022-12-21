"""The edilkamin integration."""
from __future__ import annotations

import edilkamin

from homeassistant.components.bluetooth import async_discovered_service_info
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_NAME, CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import EdilkaminEntity
#from .fan import EdilkaminFan


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the stove with config flow."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    name = entry.data[CONF_NAME]
    if entry.data[CONF_MAC] :
        mac_address = entry.data[CONF_MAC]
        entities = [EdilkaminEntity(username, password, mac_address, name)]
    else :
        ble_devices = tuple(
            {"name": discovery_info.name, "address": discovery_info.address}
            for discovery_info in async_discovered_service_info(hass, False)
        )
        mac_addresses = edilkamin.discover_devices_helper(ble_devices)
        entities = [
            EdilkaminEntity(username, password, mac_address, name)
            for mac_address in mac_addresses
        ]
    async_add_entities(entities, True)
