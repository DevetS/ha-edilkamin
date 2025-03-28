"""Edilkamin integration fan entity."""
from __future__ import annotations

import edilkamin
from .const import DOMAIN, FAN_SPEED_PERCENTAGE, FAN_PERCENTAGE_SPEED, LOGGER

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature
)

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the stove with config flow."""
    name = entry.data[CONF_NAME]
    coordinator = hass.data[DOMAIN]["coordinator"]

    await coordinator.async_request_refresh()
    fan_number = coordinator.data["nvm"]["installer_parameters"]["fans_number"]

    if fan_number == 1:
        return
    else:
        entities = [
            EdilkaminFan(coordinator, i, name)
            for i in range(2, fan_number + 1)
        ]
        async_add_entities(entities, True)


class EdilkaminFan(CoordinatorEntity, FanEntity):
    """Representation of a stove fan."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = ["auto", "none"]
    _attr_speed_count = 5

    def __init__(
        self,
        coordinator,
        fan_index: int,
        name: str,
    ) -> None:
        """Create the Edilkamin Fan entity."""
        super().__init__(coordinator)

        self._mac_address = coordinator.get_mac()

        self._attr_name = f"{name} Fan {fan_index}"
        self._attr_unique_id = f"{self._mac_address}_fan{fan_index}"
        self._fan_index = fan_index
        self._mqtt_command = f"fan_{self._fan_index}_speed"
        self._device_info = self.coordinator.data

        self._attr_device_info = {
            "identifiers": {("edilkamin", self._mac_address)}
        }

        # Initial values
        self._attr_percentage = 0
        self._attr_preset_mode = "auto"

        self._attr_extra_state_attributes = {}

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._device_info = self.coordinator.data

        if not self._device_info:
            return

        key = f"fan_{self._fan_index}_ventilation"
        speed = self._device_info["nvm"]["user_parameters"][key]
        if speed == 6:
            self._attr_preset_mode = "auto"
        else:
            self._attr_preset_mode = "none"
            self._attr_percentage = FAN_SPEED_PERCENTAGE[speed]
        self._attr_extra_state_attributes["actual_speed"] = (
            self._device_info["status"]["fans"][f"fan_{self._fan_index}_speed"]
        )

        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        LOGGER.debug("Setting async percentage: %s", percentage)

        fan_speed = FAN_PERCENTAGE_SPEED[percentage]
        token = self.coordinator.get_token()
        payload = {"name": f"fan_{self._fan_index}_speed", "value": fan_speed}

        await self.hass.async_add_executor_job(
            edilkamin.mqtt_command,
            token, self._mac_address,
            payload
        )
        await self.coordinator.async_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        LOGGER.debug("Setting async fan mode: %s", preset_mode)

        token = self.coordinator.get_token()
        if preset_mode == "auto":
            payload = {"name": self._mqtt_command, "value": 2}
        else:
            fan_speed = FAN_PERCENTAGE_SPEED[self._attr_percentage]
            payload = {"name": self._mqtt_command, "value": fan_speed}

        await self.hass.async_add_executor_job(
            edilkamin.mqtt_command,
            token,
            self._mac_address,
            payload
        )
        await self.coordinator.async_refresh()

    async def async_turn_on(
        self,
        speed=None,
        percentage=None,
        preset_mode=None,
        **kwargs
    ) -> None:
        """Turn the fan on"""
        token = self.coordinator.get_token()
        if preset_mode == "auto" or self._attr_preset_mode == "auto":
            payload = {"name": self._mqtt_command, "value": 6}
        else:
            if percentage:
                fan_speed = FAN_PERCENTAGE_SPEED[percentage]
            else:
                fan_speed = FAN_PERCENTAGE_SPEED[self._attr_percentage]
            payload = {"name": self._mqtt_command, "value": fan_speed}

        await self.hass.async_add_executor_job(
            edilkamin.mqtt_command,
            token,
            self._mac_address,
            payload
        )
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""

        token = self.coordinator.get_token()
        payload = {"name": self._mqtt_command, "value": 0}

        await self.hass.async_add_executor_job(
            edilkamin.mqtt_command,
            token,
            self._mac_address,
            payload
        )
        await self.coordinator.async_refresh()

    @property
    def is_on(self) -> bool:
        """ Return if the fan is on"""
        power = edilkamin.device_info_get_power(self._device_info)
        if power == edilkamin.Power.OFF:
            return False
        else:
            return self._attr_percentage != 0
