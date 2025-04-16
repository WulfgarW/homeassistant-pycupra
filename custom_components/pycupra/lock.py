"""
Support for My Cupra Platform
"""
import logging

from homeassistant.components.lock import LockEntity
from homeassistant.const import CONF_RESOURCES

from . import DATA, DATA_KEY, DOMAIN, PyCupraEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ Setup the PyCupra lock """
    if discovery_info is None:
        return

    async_add_entities([PyCupraLock(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        if CONF_RESOURCES in entry.options:
            resources = entry.options[CONF_RESOURCES]
        else:
            resources = entry.data[CONF_RESOURCES]

        async_add_devices(
            PyCupraLock(data, instrument.vehicle_name, instrument.component, instrument.attr)
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "lock" and instrument.attr in resources
            )
        )

    return True


class PyCupraLock(PyCupraEntity, LockEntity):
    """Represents a PyCupra Connect Lock."""

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self.instrument.is_locked

    async def async_lock(self, **kwargs):
        """Lock the car."""
        await self.instrument.lock()
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs):
        """Unlock the car."""
        await self.instrument.unlock()
        self.async_write_ha_state()
