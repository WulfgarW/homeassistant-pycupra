"""
Support for My Cupra Platform
"""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import CONF_RESOURCES, STATE_UNKNOWN


from . import DATA, DATA_KEY, DOMAIN, PyCupraEntity, UPDATE_CALLBACK, async_show_pycupra_notification

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ Setup the PyCupra number."""
    if discovery_info is None:
        return
    async_add_entities([PyCupraNumber(hass.data[DATA_KEY], *discovery_info)])


async def async_setup_entry(hass, entry, async_add_devices):
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator
    if coordinator.data is not None:
        if CONF_RESOURCES in entry.options:
            resources = entry.options[CONF_RESOURCES]
        else:
            resources = entry.data[CONF_RESOURCES]

        async_add_devices(
            PyCupraNumber(
                data, instrument.vehicle_name, instrument.component, instrument.attr
            )
            for instrument in (
                instrument
                for instrument in data.instruments
                if instrument.component == "number" and instrument.attr in resources
            )
        )

    return True


class PyCupraNumber(PyCupraEntity, NumberEntity):
    """Representation of a PyCupra Number."""

    _attr_entity_category = EntityCategory.CONFIG

    @property
    def native_min_value(self):
        if self.instrument is not None:
            if self.instrument.min_value:
                return self.instrument.min_value
        return 0

    @property
    def native_max_value(self):
        if self.instrument is not None:
            if self.instrument.max_value:
                return self.instrument.max_value
        return 100

    @property
    def native_step(self):
        if self.instrument is not None:
            if self.instrument.step:
                return self.instrument.step
        return 10

    @property
    def native_value(self):
        if self.instrument is not None:
            if self.instrument.value:
                return float(self.instrument.value)
        return STATE_UNKNOWN

    @property
    def native_unit_of_measurement(self):
        if self.instrument is not None:
            if self.instrument.unit:
                return self.instrument.unit
        return None

    async def async_set_native_value(self, value) -> None:
        try:
            if self.instrument.mutable:
                await self.instrument.set_value(int(value))
                self.async_write_ha_state()
            else:
                _LOGGER.warning(f"Not changing value of '{self.instrument.attr}', because the option \'mutable\' is deactivated or the instrument is not changeable for your vehicle.")
                async_show_pycupra_notification(self.hass, f"Not changing value of '{self.instrument.attr}', because the option \'mutable\' is deactivated or the instrument is not changeable for your vehicle.", title="Option mutable deactivated", id="PyCupra_mutable")
        except Exception as e:
            _LOGGER.error(f"An error occurred, while trying to change value of '{self.instrument.attr}'. Error: {e}")
            async_show_pycupra_notification(self.hass, f"An error occurred, while trying to change value of '{self.instrument.attr}'. Error: {e}", title="Set number error", id="PyCupra_set_number_error")

