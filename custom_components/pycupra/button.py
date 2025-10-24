"""Support for PyCupra buttons."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_RESOURCES

from . import DATA, DATA_KEY, DOMAIN, PyCupraEntity, UPDATE_CALLBACK
from .const import BUTTON_INSTRUMENTS

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up PyCupra buttons from discovery."""
    if discovery_info is None:
        return

    async_add_entities([PyCupraButton(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up PyCupra buttons from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator

    if coordinator.data is not None:
        if CONF_RESOURCES in entry.options:
            resources = entry.options[CONF_RESOURCES]
        else:
            resources = entry.data[CONF_RESOURCES]

        new_devices = []
        for instrument in data.instruments:
            if (
                instrument.component == "switch"
                and instrument.attr in BUTTON_INSTRUMENTS
                and instrument.attr in resources
            ):
                _LOGGER.debug(
                    "Instrument %s added to button platform", instrument.attr
                )
                new_devices.append(
                    PyCupraButton(
                        data,
                        instrument.vehicle_name,
                        instrument.component,
                        instrument.attr,
                        hass.data[DOMAIN][entry.entry_id][UPDATE_CALLBACK],
                    )
                )

        if new_devices:
            async_add_devices(new_devices)

    return True


class PyCupraButton(PyCupraEntity, ButtonEntity):
    """Representation of a PyCupra button."""

    @property
    def available(self) -> bool:
        """Return availability of the button."""
        return self.instrument is not None

    async def async_press(self) -> None:
        """Handle button press."""
        instrument = self.instrument

        if instrument is None:
            _LOGGER.debug("Button %s has no instrument", self.name)
            return

        _LOGGER.debug("Pressing button %s", instrument.attr)
        await instrument.turn_on()
        self.async_write_ha_state()

