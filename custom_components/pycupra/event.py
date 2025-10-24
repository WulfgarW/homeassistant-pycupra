"""Event entity for PyCupra Firebase notifications."""

from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.components.event import EventEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DATA, DOMAIN, SIGNAL_FIREBASE_EVENT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities) -> bool:
    """Set up the Firebase event entity."""
    data = hass.data[DOMAIN][entry.entry_id][DATA]
    coordinator = data.coordinator

    if coordinator is None or not coordinator.firebaseWanted:
        return True

    async_add_entities([PyCupraFirebaseEventEntity(data)])
    return True


class PyCupraFirebaseEventEntity(EventEntity):
    """Representation of the Firebase event entity."""

    _attr_event_types = ["firebase_event"]
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:car-connected"

    def __init__(self, data) -> None:
        """Initialise the Firebase event entity."""
        self._data = data
        self.coordinator = data.coordinator
        self._unsub_dispatcher: Callable[[], None] | None = None
        self._attr_unique_id = f"{self.coordinator.vin}-firebase-event"
        self._attr_name = f"{self._vehicle_name} Firebase event"

    @property
    def _vehicle_name(self) -> str:
        """Return the friendly vehicle name."""
        try:
            vehicle = self.coordinator.connection.vehicle(self.coordinator.vin)
            return self._data.vehicle_name(vehicle)
        except Exception as err:  # pragma: no cover - defensive
            _LOGGER.debug("Failed to determine vehicle name for firebase event entity: %s", err)
            return self.coordinator.vin

    @property
    def device_info(self) -> dict[str, Any]:
        """Return the device information for the associated vehicle."""
        try:
            vehicle = self.coordinator.connection.vehicle(self.coordinator.vin)
            return {
                "identifiers": {(DOMAIN, vehicle.vin)},
                "name": self._data.vehicle_name(vehicle),
                "manufacturer": vehicle.brand,
                "model": vehicle.model,
                "sw_version": vehicle.model_year,
            }
        except Exception as err:  # pragma: no cover - defensive
            _LOGGER.debug("Failed to build device info for firebase event entity: %s", err)
            return {"identifiers": {(DOMAIN, self.coordinator.vin)}}

    async def async_added_to_hass(self) -> None:
        """Register callbacks when the entity is added to Home Assistant."""
        await super().async_added_to_hass()

        def _handle_event(event_data: dict[str, Any]) -> None:
            self._trigger_event("firebase_event", event_data)
            self.async_write_ha_state()

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            SIGNAL_FIREBASE_EVENT,
            _handle_event,
        )

        if self.coordinator.firebase_last_event is not None:
            _handle_event(self.coordinator.firebase_last_event)

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect dispatcher when entity is removed."""
        await super().async_will_remove_from_hass()
        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None
