"""
Support for My Cupra Platform
"""
import logging
from typing import Any, Dict, Optional
import voluptuous as vol

from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.const import CONF_RESOURCES

from . import DATA, DATA_KEY, DOMAIN, PyCupraEntity, UPDATE_CALLBACK
from .const import BUTTON_INSTRUMENTS

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ Setup the PyCupra switch."""
    if discovery_info is None:
        return
    async_add_entities([PyCupraSwitch(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        if CONF_RESOURCES in entry.options:
            resources = entry.options[CONF_RESOURCES]
        else:
            resources = entry.data[CONF_RESOURCES]

        newDevices=[]
        for instrument in data.instruments:
            if instrument.component == "switch" and instrument.attr in resources:
                if instrument.attr in BUTTON_INSTRUMENTS:
                    continue
                #_LOGGER.debug(f"In switch.py.async_setup_entry. Instrument: {instrument.attr}")
                if instrument.attr in ('departure1','departure2','departure3','departure_profile1','departure_profile2','departure_profile3', 'request_flash', 'request_honkandflash'):
                    _LOGGER.debug(f"Instrument {instrument.attr} added without callback")
                    newDevices.append(PyCupraSwitch(data, instrument.vehicle_name, instrument.component, instrument.attr))
                else:
                    _LOGGER.debug(f"Instrument {instrument.attr} added with callback")
                    newDevices.append(PyCupraSwitch(data, instrument.vehicle_name, instrument.component, instrument.attr, hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK]))
        async_add_devices(newDevices)

    return True


class PyCupraSwitch(PyCupraEntity, ToggleEntity):
    """Representation of a PyCupra Switch."""

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self.instrument.state

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug(f"Turning on switch {self.instrument.attr}")
        await self.instrument.turn_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug(f"Turning off switch {self.instrument.attr}")
        await self.instrument.turn_off()
        self.async_write_ha_state()

    @property
    def assumed_state(self):
        return self.instrument.assumed_state

    @property
    def state_attributes(self) -> Optional[Dict[str, Any]]:
        return self.instrument.attributes
