# -*- coding: utf-8 -*-
"""
PyCupra integration

Read more at https://github.com/WulfgarW/homeassistant-pycupra/
"""
import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Union
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, SOURCE_REAUTH, SOURCE_IMPORT
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_RESOURCES,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME, EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.redact import REDACTED, async_redact_data

from pycupra.connection import Connection
from pycupra.vehicle import Vehicle
from pycupra.exceptions import (
    SeatConfigException,
    SeatAuthenticationException,
    SeatAccountLockedException,
    SeatTokenExpiredException,
    SeatException,
    SeatEULAException,
    SeatThrottledException,
    SeatLoginFailedException,
    SeatInvalidRequestException,
    SeatRequestInProgressException
)

from .const import (
    PLATFORMS,
    BUTTON_INSTRUMENTS,
    CONF_BRAND,
    CONF_MUTABLE,
    #CONF_SCANDINAVIAN_MILES,
    CONF_SPIN,
    CONF_VEHICLE,
    CONF_INSTRUMENTS,
    CONF_NIGHTLY_UPDATE_REDUCTION,
    CONF_FIREBASE,
    DATA,
    DATA_KEY,
    MIN_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SIGNAL_STATE_UPDATED,
    UNDO_UPDATE_LISTENER, UPDATE_CALLBACK, CONF_DEBUG, DEFAULT_DEBUG, CONF_CONVERT, CONF_NO_CONVERSION,
    CONF_IMPERIAL_UNITS,
    SERVICE_SET_SCHEDULE,
    SERVICE_SET_DEPARTURE_PROFILE_SCHEDULE,
    SERVICE_SET_MAX_CURRENT,
    SERVICE_SEND_DESTINATION,
    SERVICE_SET_CHARGE_LIMIT,
    SERVICE_SET_TARGET_SOC,
    SERVICE_SET_CLIMATER,
    SERVICE_SET_PHEATER_DURATION,
)

SERVICE_SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("id"): vol.In([1,2,3]),
        vol.Required("time"): cv.string,
        vol.Required("enabled"): cv.boolean,
        vol.Required("recurring"): cv.boolean,
        vol.Optional("date"): cv.string,
        vol.Optional("days"): cv.string,
        #vol.Optional("temp"): vol.All(vol.Coerce(int), vol.Range(min=16, max=30)),
        vol.Optional("temp"): vol.In([16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0, 23.5, 
                                      24.0, 24.5, 25.0, 25.5, 26.0, 26.5, 27.0, 27.5, 28.0, 28,5, 29.0, 29.5, 30.0]), 
        vol.Optional("climatisation"): cv.boolean,
        vol.Optional("charging"): cv.boolean,
        vol.Optional("charge_current"): vol.Any(
            vol.Range(min=1, max=254),
            vol.In(['Maximum', 'maximum', 'Max', 'max', 'Minimum', 'minimum', 'Min', 'min', 'Reduced', 'reduced'])
        ),
        vol.Optional("charge_target"): vol.In([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]),
        vol.Optional("off_peak_active"): cv.boolean,
        vol.Optional("off_peak_start"): cv.string,
        vol.Optional("off_peak_end"): cv.string,
    }
)
SERVICE_SET_DEPARTURE_PROFILE_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("id"): vol.In([1,2,3]),
        vol.Required("time"): cv.string,
        vol.Required("enabled"): cv.boolean,
        vol.Required("recurring"): cv.boolean,
        vol.Optional("date"): cv.string,
        vol.Optional("days"): cv.string,
        vol.Required("chargingProgramId"): vol.In([1,2,3,4,5,6,7,8,9,10]),
    }
)
SERVICE_SET_MAX_CURRENT_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("current"): vol.Any(
            vol.Range(min=1, max=255),
            vol.In(['Maximum', 'maximum', 'Max', 'max', 'Minimum', 'minimum', 'Min', 'min', 'Reduced', 'reduced'])
        ),
    }
)
SERVICE_SET_TARGET_SOC_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("targetSoc"): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    }
)
SERVICE_SET_CHARGE_LIMIT_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("limit"): vol.In([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]),
    }
)
SERVICE_SEND_DESTINATION_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("latitude"): vol.All(vol.Coerce(float), vol.Range(min=-90, max=90)),
        vol.Required("longitude"): vol.All(vol.Coerce(float), vol.Range(min=-180, max=180)),
        vol.Required("poiProvider"): cv.string,
        vol.Optional("destinationName"): cv.string,
        vol.Optional("street"): cv.string,
        vol.Optional("houseNumber"): cv.string,
        vol.Optional("city"): cv.string,
        vol.Optional("zipCode"): cv.string,
        vol.Optional("country"): cv.string,
        vol.Optional("stateAbbrevation"): cv.string,
    }
)
SERVICE_SET_CLIMATER_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("enabled", default='Start'): vol.In(['Start', 'Stop', 'Set Temp.']),
        vol.Optional("temp"): vol.In([16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0, 23.5, 
                                      24.0, 24.5, 25.0, 25.5, 26.0, 26.5, 27.0, 27.5, 28.0, 28,5, 29.0, 29.5, 30.0]), 
        #vol.Optional("battery_power"): cv.boolean,
        vol.Optional("aux_heater"): cv.boolean,
        vol.Optional("spin"): vol.All(cv.string, vol.Match(r"^[0-9]{4}$"))
    }
)
SERVICE_SET_PHEATER_DURATION_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.string, vol.Length(min=32, max=32)),
        vol.Required("duration"): vol.In([10, 20, 30, 40, 50, 60]),
    }
)

# Set max parallel updates to 2 simultaneous (1 poll and 1 request waiting)
#PARALLEL_UPDATES = 2

_LOGGER = logging.getLogger(__name__)
TOKEN_FILE_NAME_AND_PATH='./custom_components/pycupra/pycupra_token.json'
FIREBASE_CREDENTIALS_FILE_NAME_AND_PATH='./custom_components/pycupra/pycupra_firebase_credentials.json'

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Setup PyCupra component from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    if entry.options.get(CONF_SCAN_INTERVAL):
        update_interval = timedelta(seconds=entry.options[CONF_SCAN_INTERVAL])
    else:
        update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
    if update_interval < timedelta(seconds=MIN_SCAN_INTERVAL):
        update_interval = timedelta(seconds=MIN_SCAN_INTERVAL)

    coordinator = PyCupraCoordinator(hass, entry, update_interval)

    try:
        if not await coordinator.async_login():
            await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_REAUTH},
                data=entry,
            )
            return False
    except (SeatAuthenticationException, SeatAccountLockedException, SeatLoginFailedException) as e:
        raise ConfigEntryAuthFailed(e) from e
    except Exception as e:
        raise ConfigEntryNotReady(e) from e

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, coordinator.async_logout)
    )

    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    # Get parent device
    try:
        identifiers={(DOMAIN, entry.unique_id)}
        registry = device_registry.async_get(hass)
        device = registry.async_get_device(identifiers)
        # Get user configured name for device
        name = device.name_by_user if not device.name_by_user is None else None
    except:
        name = None

    data = PyCupraData(entry.data, name, coordinator)
    instruments = coordinator.data

    conf_instruments = entry.data.get(CONF_INSTRUMENTS, {}).copy()
    if entry.options.get(CONF_DEBUG, False) is True:
        _LOGGER.debug(f"Configured data: {async_redact_data(entry.data, ['username', 'password', 'vehicle', 'spin'])}") 
        _LOGGER.debug(f"Configured options: {async_redact_data(entry.options, ['username', 'password', 'vehicle', 'spin'])}") 
        _LOGGER.debug(f"Resources from options are: {entry.options.get(CONF_RESOURCES, [])}")
        _LOGGER.debug(f"All instruments (data): {conf_instruments}")
    new_instruments = {}

    def is_enabled(attr):
        """Return true if the user has enabled the resource."""
        return attr in entry.data.get(CONF_RESOURCES, [attr])

    components = set()

    # Check if new instruments
    for instrument in (
        instrument
        for instrument in instruments
        if not instrument.attr in conf_instruments
    ):
            _LOGGER.info(f"Discovered new instrument {instrument.name}")
            new_instruments[instrument.attr] = instrument.name

    # Update config entry with new instruments
    if len(new_instruments) > 0:
        conf_instruments.update(new_instruments)
        # Prepare data to update config entry with
        update = {
            'data': {
                CONF_INSTRUMENTS: dict(sorted(conf_instruments.items(), key=lambda item: item[1]))
            },
            'options': {
                CONF_RESOURCES: entry.options.get(
                    CONF_RESOURCES,
                    entry.data.get(CONF_RESOURCES, ['none']))
            }
        }

        # Enable new instruments if "activate newly enable entitys" is active
        if hasattr(entry, "pref_disable_new_entities"):
            if not entry.pref_disable_new_entities:
                _LOGGER.debug(f"Enabling new instruments {new_instruments}")
                for item in new_instruments:
                    update['options'][CONF_RESOURCES].append(item)

        _LOGGER.debug(f"Updating config entry data: {update.get('data')}")
        _LOGGER.debug(f"Updating config entry options: {update.get('options')}")
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, **update['data']},
            options={**entry.options, **update['options']}
        )

    for instrument in (
        instrument
        for instrument in instruments
        if instrument.component in PLATFORMS and is_enabled(instrument.slug_attr)
    ):
        data.instruments.add(instrument)
        if instrument.component == "switch" and instrument.attr in BUTTON_INSTRUMENTS:
            components.add("button")
        else:
            components.add(PLATFORMS[instrument.component])

    hass.data[DOMAIN][entry.entry_id] = {
        UPDATE_CALLBACK: update_callback,
        DATA: data,
        UNDO_UPDATE_LISTENER: entry.add_update_listener(_async_update_listener),
    }

    for component in components:
        coordinator.platforms.append(component)
        #await hass.config_entries.async_forward_entry_setups(entry, [component])
        #hass.async_create_task(
        #    hass.config_entries.async_forward_entry_setups(entry, [component])
        #)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, components)
    )

    # Service functions
    async def get_car(service_call):
        """Get VIN associated with HomeAssistant device ID."""
        # Get device entry
        dev_id = service_call.data.get("device_id")
        dev_reg = device_registry.async_get(hass)
        dev_entry = dev_reg.async_get(dev_id)

        # Get vehicle VIN from device identifiers
        seat_identifiers = [
            identifier
            for identifier in dev_entry.identifiers
            if identifier[0] == DOMAIN
        ]
        vin_identifier = next(iter(seat_identifiers))
        vin = vin_identifier[1]

        # Get coordinator handling the device entry
        conf_entry = next(iter(dev_entry.config_entries))
        try:
            dev_coordinator = hass.data[DOMAIN][conf_entry]['data'].coordinator
        except:
            raise SeatConfigException('Could not find associated coordinator for given vehicle')

        # Return with associated Vehicle class object
        return dev_coordinator.connection.vehicle(vin)

    async def set_schedule(service_call=None):
        """Set departure schedule."""
        try:
            # Prepare data
            id = service_call.data.get("id", 0)
            temp = None

            # Convert datetime objects to simple strings or check that strings are correctly formatted
            try:
                time = service_call.data.get("time").strftime("%H:%M")
            except:
                if re.match('^[0-9]{2}:[0-9]{2}$', service_call.data.get('time', '')):
                    time = service_call.data.get("time", "08:00")
                else:
                    raise SeatInvalidRequestException(f"Invalid time string: {service_call.data.get('time')}")
            if service_call.data.get("off_peak_start", False):
                try:
                    peakstart = service_call.data.get("off_peak_start").strftime("%H:%M")
                except:
                    if re.match('^[0-9]{2}:[0-9]{2}$', service_call.data.get("off_peak_start", "")):
                        time = service_call.data.get("off_peak_start", "00:00")
                    else:
                        raise SeatInvalidRequestException(f"Invalid value for off peak start hours: {service_call.data.get('off_peak_start')}")
            if service_call.data.get("off_peak_end", False):
                try:
                    peakend = service_call.data.get("off_peak_end").strftime("%H:%M")
                except:
                    if re.match('^[0-9]{2}:[0-9]{2}$', service_call.data.get("off_peak_end", "")):
                        time = service_call.data.get("off_peak_end", "00:00")
                    else:
                        raise SeatInvalidRequestException(f"Invalid value for off peak end hours: {service_call.data.get('off_peak_end')}")

            # Convert to parseable data
            schedule = {
                "id": service_call.data.get("id", 1),
                "enabled": service_call.data.get("enabled"),
                "recurring": service_call.data.get("recurring"),
                "date": service_call.data.get("date"),
                "time": time,
                "days": service_call.data.get("days", "nnnnnnn"),
            }
            # Set optional values
            # Night rate
            if service_call.data.get("climatisation", None) is not None:
                schedule["nightRateActive"] = service_call.data.get("climatisation")
            if service_call.data.get("off_peak_start", None) is not None:
                schedule["nightRateTimeStart"] = service_call.data.get("off_peak_start")
            if service_call.data.get("off_peak_end", None) is not None:
                schedule["nightRateTimeEnd"] = service_call.data.get("off_peak_end")
            # Climatisation and charging options
            if service_call.data.get("climatisation", None) is not None:
                schedule["operationClimatisation"] = service_call.data.get("climatisation")
            if service_call.data.get("charging", None) is not None:
                schedule["operationCharging"] = service_call.data.get("charging")
            if service_call.data.get("charge_target", None) is not None:
                schedule["targetChargeLevel"] = service_call.data.get("charge_target")
            if service_call.data.get("charge_current", None) is not None:
                schedule["chargeMaxCurrent"] = service_call.data.get("charge_current")
            # Global optional options
            if service_call.data.get("temp", None) is not None:
                schedule["targetTemp"] = service_call.data.get("temp")

            # Find the correct car and execute service call
            car = await get_car(service_call)
            _LOGGER.info(f'Set departure schedule {id} with data {schedule} for car {car.vin}')
            if await car.set_timer_schedule(id, schedule) is True:
                _LOGGER.debug(f"Service call 'set_schedule' executed without error")
                await coordinator.async_request_refresh()
            else:
                _LOGGER.warning(f"Failed to execute service call 'set_schedule' with data '{service_call}'")
        except (SeatInvalidRequestException) as e:
            _LOGGER.warning(f"Service call 'set_schedule' failed {e}")
        except Exception as e:
            raise

    async def set_departure_profile_schedule(service_call=None):
        """Set departure profile schedule."""
        try:
            # Prepare data
            id = service_call.data.get("id", 0)
            temp = None

            # Convert datetime objects to simple strings or check that strings are correctly formatted
            try:
                time = service_call.data.get("time").strftime("%H:%M")
            except:
                if re.match('^[0-9]{2}:[0-9]{2}$', service_call.data.get('time', '')):
                    time = service_call.data.get("time", "08:00")
                else:
                    raise SeatInvalidRequestException(f"Invalid time string: {service_call.data.get('time')}")

            # Convert to parseable data
            schedule = {
                "id": service_call.data.get("id", 1),
                "enabled": service_call.data.get("enabled"),
                "recurring": service_call.data.get("recurring"),
                "date": service_call.data.get("date"),
                "time": time,
                "days": service_call.data.get("days", "nnnnnnn"),
                "chargingProgramId": service_call.data.get("chargingProgramId", 1),
            }

            # Find the correct car and execute service call
            car = await get_car(service_call)
            _LOGGER.info(f'Set departure profile schedule {id} with data {schedule} for car {car.vin}')
            if await car.set_departure_profile_schedule(id, schedule) is True:
                _LOGGER.debug(f"Service call 'set_departure_profile_schedule' executed without error")
                await coordinator.async_request_refresh()
            else:
                _LOGGER.warning(f"Failed to execute service call 'set_departure_profile_schedule' with data '{service_call}'")
        except (SeatInvalidRequestException) as e:
            _LOGGER.warning(f"Service call 'set_departure_profile_schedule' failed {e}")
        except Exception as e:
            raise

    async def send_destination(service_call=None):
        """Send destination to vehicle."""
        try:
            car = await get_car(service_call)

            # Get destination data and execute service call
            latitude = service_call.data.get("latitude", 0)
            longitude = service_call.data.get("longitude", 0)
            destinationName = service_call.data.get("destinationName", '')
            poiProvider = service_call.data.get("poiProvider", '')
            street = service_call.data.get("street", '')
            houseNumber = service_call.data.get("houseNumber", '')
            city = service_call.data.get("city", '')
            zipCode = service_call.data.get("zipCode", '')
            country = service_call.data.get("country", '')
            stateAbbrevation = service_call.data.get("stateAbbrevation", '')
            dest = {
                "poiProvider": poiProvider,                                     	         # poiProvider mandatory
                "geoCoordinate":{"latitude": latitude,"longitude":longitude},  # geoCoordinate mandatory
                "destinationName": destinationName
            }
            if city != '':
                dest["address"]= {
	  "street": street,
	  "houseNumber": houseNumber,
	  "city": city,
	  "zipCode": zipCode,
	  "country": country,
	  "stateAbbrevation": stateAbbrevation,
	  }

            _LOGGER.debug(f"destination dict= {dest}")
            if await car.send_destination(dest) is True:
                _LOGGER.debug(f"Service call 'send_destination' executed without error")
            else:
                _LOGGER.warning(f"Failed to execute service call 'send_destination' with data '{service_call}'")
        except (SeatInvalidRequestException) as e:
            _LOGGER.warning(f"Service call 'send_destination' failed {e}")
        except Exception as e:
            raise

    async def set_charge_limit(service_call=None):
        """Set minimum charge limit."""
        try:
            car = await get_car(service_call)

            # Get charge limit and execute service call
            limit = service_call.data.get("limit", 50)
            if await car.set_charge_limit(limit) is True:
                _LOGGER.debug(f"Service call 'set_charge_limit' executed without error")
                await coordinator.async_request_refresh()
            else:
                _LOGGER.warning(f"Failed to execute service call 'set_charge_limit' with data '{service_call}'")
        except (SeatInvalidRequestException) as e:
            _LOGGER.warning(f"Service call 'set_charge_limit' failed {e}")
        except Exception as e:
            raise

    async def set_current(service_call=None):
        """Set charge current."""
        try:
            car = await get_car(service_call)

            # Get charge current and execute service call
            current = service_call.data.get('current', None)
            if await car.set_charger_current(current) is True:
                _LOGGER.debug(f"Service call 'set_current' executed without error")
                await coordinator.async_request_refresh()
            else:
                _LOGGER.warning(f"Failed to execute service call 'set_current' with data '{service_call}'")
        except (SeatInvalidRequestException) as e:
            _LOGGER.warning(f"Service call 'set_current' failed {e}")
        except Exception as e:
            raise

    async def set_target_soc(service_call=None):
        """Set target state of charge."""
        try:
            car = await get_car(service_call)

            # Get charge current and execute service call
            targetSoc = service_call.data.get('targetSoc', None)
            if await car.set_charger_target_soc(targetSoc) is True:
                _LOGGER.debug(f"Service call 'set_target_soc' executed without error")
                await coordinator.async_request_refresh()
            else:
                _LOGGER.warning(f"Failed to execute service call 'set_target_soc' with data '{service_call}'")
        except (SeatInvalidRequestException) as e:
            _LOGGER.warning(f"Service call 'set_target_soc' failed {e}")
        except Exception as e:
            raise

    async def set_pheater_duration(service_call=None):
        """Set duration for parking heater."""
        try:
            car = await get_car(service_call)
            car.pheater_duration = service_call.data.get("duration", car.pheater_duration)
            _LOGGER.debug(f"Service call 'set_pheater_duration' executed without error")
            await coordinator.async_request_refresh()
        except (SeatInvalidRequestException) as e:
            _LOGGER.warning(f"Service call 'set_pheater_duration' failed {e}")
        except Exception as e:
            raise

    async def set_climater(service_call=None):
        """Start or stop climatisation with options."""
        try:
            car = await get_car(service_call)

            temp = service_call.data.get('temp', None)
            if service_call.data.get('enabled', None):
                if service_call.data.get('enabled', None)=='Set Temp.':
                    action = 'settings'
                elif service_call.data.get('enabled', None)=='Start':
                    action = 'auxiliary' if service_call.data.get('aux_heater', False) else 'electric'
                else:
                    action = 'off'
                    #temp = hvpower = spin = None
                #hvpower = service_call.data.get('battery_power', None)
                spin = service_call.data.get('spin', None)

                # Execute service call
                _LOGGER.debug(f"Action 'set_climater' with the following parameters: action={action}, temp={temp} and spin={spin}.")
                if action=='settings':
                    if temp!=None:
                        if await car.set_climatisation_temp(temp) is True:
                            _LOGGER.debug(f"Service call 'set_climater' executed without error")
                            await coordinator.async_request_refresh()
                        else:
                            _LOGGER.warning(f"Failed to execute service call 'set_climater' with data '{service_call}'")
                    else:
                        _LOGGER.warning(f"Failed to execute service call 'set_climater' because temperature parameter not set.'")
                else:
                    if await car.set_climatisation(action, temp, hvpower=None, spin=spin) is True:
                        _LOGGER.debug(f"Service call 'set_climater' executed without error")
                        await coordinator.async_request_refresh()
                    else:
                        _LOGGER.warning(f"Failed to execute service call 'set_climater' with data '{service_call}'")
            else:
                _LOGGER.warning(f"Service call 'set_climater' without valid action parameter")
        except (SeatInvalidRequestException) as e:
            _LOGGER.warning(f"Service call 'set_climater' failed {e}")
        except Exception as e:
            raise

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE,
        set_schedule,
        schema = SERVICE_SET_SCHEDULE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DEPARTURE_PROFILE_SCHEDULE,
        set_departure_profile_schedule,
        schema = SERVICE_SET_DEPARTURE_PROFILE_SCHEDULE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MAX_CURRENT,
        set_current,
        schema = SERVICE_SET_MAX_CURRENT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TARGET_SOC,
        set_target_soc,
        schema = SERVICE_SET_TARGET_SOC_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CHARGE_LIMIT,
        set_charge_limit,
        schema = SERVICE_SET_CHARGE_LIMIT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_DESTINATION,
        send_destination,
        schema = SERVICE_SEND_DESTINATION_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CLIMATER,
        set_climater,
        schema = SERVICE_SET_CLIMATER_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PHEATER_DURATION,
        set_pheater_duration,
        schema = SERVICE_SET_PHEATER_DURATION_SCHEMA
    )

    return True


def update_callback(hass, coordinator):
    _LOGGER.debug("CALLBACK!")
    hass.async_create_task(
        coordinator.async_request_refresh()
    )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the component from configuration.yaml."""
    hass.data.setdefault(DOMAIN, {})

    if hass.config_entries.async_entries(DOMAIN):
        return True

    if DOMAIN in config:
        _LOGGER.info("Found existing PyCupra configuration.")
        #await hass.config_entries.flow.async_init(
        #     DOMAIN,
        #     context={"source": SOURCE_IMPORT},
        #     data=config[DOMAIN],
        #)
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=config[DOMAIN],
            )
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading services")
    hass.services.async_remove(DOMAIN, SERVICE_SET_SCHEDULE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_MAX_CURRENT)
    hass.services.async_remove(DOMAIN, SERVICE_SET_TARGET_SOC)
    hass.services.async_remove(DOMAIN, SERVICE_SET_CHARGE_LIMIT)
    hass.services.async_remove(DOMAIN, SERVICE_SET_CLIMATER)
    hass.services.async_remove(DOMAIN, SERVICE_SET_PHEATER_DURATION)
    hass.services.async_remove(DOMAIN, SERVICE_SET_DEPARTURE_PROFILE_SCHEDULE)
    hass.services.async_remove(DOMAIN, SERVICE_SEND_DESTINATION)

    _LOGGER.debug("Unloading update listener")
    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    return await async_unload_coordinator(hass, entry)


async def async_unload_coordinator(hass: HomeAssistant, entry: ConfigEntry):
    """Unload auth token based entry."""
    _LOGGER.debug("Unloading coordinator")
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA].coordinator

    _LOGGER.debug("Log out from PyCupra")
    await coordinator.async_logout()
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        _LOGGER.debug("Unloading entry")
        del hass.data[DOMAIN][entry.entry_id]

    if not hass.data[DOMAIN]:
        _LOGGER.debug("Unloading data")
        del hass.data[DOMAIN]

    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def get_convert_conf(entry: ConfigEntry):
#    return CONF_SCANDINAVIAN_MILES if entry.options.get(
#        CONF_SCANDINAVIAN_MILES,
#        entry.data.get(
#            CONF_SCANDINAVIAN_MILES,
#            False
#        )
#    ) else CONF_NO_CONVERSION
    return CONF_NO_CONVERSION

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate configuration from old version to new."""
    _LOGGER.debug(f'Migrating from version {entry.version}')

    # Migrate data from version 1
    if entry.version == 1:
        # Make a copy of old config
        new = {**entry.data}

        # Convert from minutes to seconds for poll interval
        minutes = entry.options.get("update_interval", 1)
        seconds = minutes*60
        new.pop("update_interval", None)
        new[CONF_SCAN_INTERVAL] = seconds

        # Save "new" config
        entry.data = {**new}

        entry.version = 2

    _LOGGER.info("Migration to version %s successful", entry.version)
    return True

class PyCupraData:
    """Hold component state."""

    def __init__(self, config, name=None, coordinator=None):
        """Initialize the component state."""
        self.vehicles = set()
        self.instruments = set()
        self.config = config.get(DOMAIN, config)
        self.name = name
        self.coordinator = coordinator

    def instrument(self, vin, component, attr):
        """Return corresponding instrument."""
        return next(
            (
                instrument
                for instrument in (
                    self.coordinator.data
                    if self.coordinator is not None
                    else self.instruments
                )
                if instrument.vehicle.vin == vin
                and instrument.component == component
                and instrument.attr == attr
            ),
            None,
        )

    def vehicle_name(self, vehicle):
        """Provide a friendly name for a vehicle."""
        try:
            # Return name if configured by user
            if isinstance(self.name, str):
                if len(self.name) > 0:
                    return self.name
        except:
            pass

        # Default name to nickname if supported, else vin number
        try:
            if vehicle.is_nickname_supported:
                return vehicle.nickname
            elif vehicle.vin:
                return vehicle.vin
        except:
            _LOGGER.info(f"Name set to blank")
            return ""


class PyCupraEntity(Entity):
    """Base class for all PyCupra entities."""

    def __init__(self, data, vin, component, attribute, callback=None):
        """Initialize the entity."""

        def update_callbacks():
            if callback is not None:
                callback(self.hass, data.coordinator)

        self.data = data
        self.vin = vin
        self.component = component
        self.attribute = attribute
        self.coordinator = data.coordinator
        self.instrument.callback = update_callbacks
        self.callback = callback

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """

        # Ignore manual update requests if the entity is disabled
        if not self.enabled:
            return

        #_LOGGER.debug(f"In PyCupraEntity.async_updata. For instrument with name={self.instrument.name}, attr={self.instrument.attr}")
        await self.coordinator.update_only_selected_entity(self.instrument)
        #await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """Register update dispatcher."""
        if self.coordinator is not None:
            self.async_on_remove(
                self.coordinator.async_add_listener(self.async_write_ha_state)
            )
        else:
            self.async_on_remove(
                async_dispatcher_connect(
                    self.hass, SIGNAL_STATE_UPDATED, self.async_write_ha_state
                )
            )

    @property
    def instrument(self):
        """Return corresponding instrument."""
        return self.data.instrument(self.vin, self.component, self.attribute)

    @property
    def icon(self):
        """Return the icon."""
        if self.instrument.attr in ["battery_level", "charging"]:
            return icon_for_battery_level(
                battery_level=self.instrument.state, charging=self.vehicle.charging
            )
        return self.instrument.icon

    @property
    def vehicle(self):
        """Return vehicle."""
        return self.instrument.vehicle

    @property
    def _entity_name(self):
        return self.instrument.name

    @property
    def _vehicle_name(self):
        return self.data.vehicle_name(self.vehicle)

    @property
    def name(self):
        """Return full name of the entity."""
        return f"{self._vehicle_name} {self._entity_name}"

    @property
    def should_poll(self) -> bool:
        """Return the polling state."""
        return False

    @property
    def assumed_state(self) -> bool:
        """Return true if unable to access real state of entity."""
        return True

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        attributes = dict(
            self.instrument.attributes,
            model=f"{self.vehicle.model}/{self.vehicle.model_year}",
        )

        # Return model image as picture attribute for position entity
        if "position" in self.attribute:
            # Try to use small thumbnail first hand, else fallback to fullsize
            if self.vehicle.is_model_image_small_supported:
                attributes["entity_picture"] = self.vehicle.model_image_small
            elif self.vehicle.is_model_image_large_supported:
                attributes["entity_picture"] = self.vehicle.model_image_large

        return attributes

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(DOMAIN, self.vin)},
            "name": self._vehicle_name,
            "manufacturer": self.vehicle.brand,
            "model": self.vehicle.model,
            "sw_version": self.vehicle.model_year,
        }

    @property
    def available(self):
        """Return if sensor is available."""
        if self.data.coordinator is not None:
            return self.data.coordinator.last_update_success
        return True

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.vin}-{self.component}-{self.attribute}"


class PyCupraCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, entry, update_interval: timedelta):
        self.vin = entry.data[CONF_VEHICLE].upper()
        self.entry = entry
        self.platforms = []
        self.report_last_updated = None
        self.connection = Connection(
            session=async_get_clientsession(hass),
            brand=self.entry.data[CONF_BRAND],
            username=self.entry.data[CONF_USERNAME],
            password=self.entry.data[CONF_PASSWORD],
            fulldebug=self.entry.options.get(CONF_DEBUG, self.entry.data.get(CONF_DEBUG, DEFAULT_DEBUG)),
            nightlyUpdateReduction=self.entry.options.get(CONF_NIGHTLY_UPDATE_REDUCTION, self.entry.data.get(CONF_NIGHTLY_UPDATE_REDUCTION, False)),
        )
        self.firebaseWanted=self.entry.options.get(CONF_FIREBASE, self.entry.data.get(CONF_FIREBASE, False))
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self):
        """Update data via library."""
        vehicle = await self.update()

        if not vehicle:
            raise UpdateFailed("No vehicles found.")

        # Backward compatibility
        #default_convert_conf = get_convert_conf(self.entry)

        #convert_conf = self.entry.options.get(
        #    CONF_CONVERT,
        #    self.entry.data.get(
        #        CONF_CONVERT,
        #        default_convert_conf
        #    )
        #)

        dashboard = vehicle.dashboard(
            mutable=self.entry.options.get(CONF_MUTABLE),
            spin=self.entry.options.get(CONF_SPIN),
            #miles=convert_conf == CONF_IMPERIAL_UNITS,
            #scandinavian_miles=convert_conf == CONF_SCANDINAVIAN_MILES,
        )

        return dashboard.instruments

    async def async_logout(self, event=None) -> bool:
        """Logout from Cupra/Seat portal"""
        _LOGGER.debug("Shutdown PyCupra")
        try:
            await self.connection.terminate()
            self.connection = None
        except Exception as ex:
            _LOGGER.error("Failed to log out and revoke tokens for Cupra/Seat portal. Some tokens might still be valid.")
            return False
        return True

    async def async_login(self) -> bool:
        """Login to Cupra/Seat portal"""
        # Check if we can login
        try:
            if await self.connection.doLogin(tokenFile=TOKEN_FILE_NAME_AND_PATH) is False:
                _LOGGER.warning(
                    "Could not login to Cupra/Seat portal, please check your credentials and verify that the service is working"
                )
                return False
            # Get associated vehicles before we continue
            await self.connection.get_vehicles()
            return True
        except (SeatAccountLockedException, SeatAuthenticationException) as e:
            # Raise auth failed error in config flow
            raise ConfigEntryAuthFailed(e) from e
        except:
            raise

    async def update(self) -> Union[bool, Vehicle]:
        """Update data from API"""

        # Update vehicle data
        _LOGGER.debug("Updating data from Cupra/Seat API")
        try:
            # Get Vehicle object matching VIN number
            vehicle = self.connection.vehicle(self.vin)
            if self.firebaseWanted:
                newStatus = await vehicle.initialiseFirebase(firebaseCredentialsFileName=FIREBASE_CREDENTIALS_FILE_NAME_AND_PATH, updateCallback=self.updateCallbackForNotifications)
                #_LOGGER.debug(f"New status of firebase={newStatus}")
            if await vehicle.update():
                return vehicle
            else:
                _LOGGER.warning("Could not query update from Cupra/Seat API")
                return False
        except Exception as error:
            _LOGGER.warning(f"An error occured while requesting update from Cupra/Seat API: {error}")
            return False

    async def updateCallbackForNotifications(self, updateType=0) -> Union[bool, Vehicle]:
        """Update status from API (called for notifications)"""

        # Update vehicle data
        _LOGGER.debug("Due to push notification, call for update of data from Cupra/Seat API")
        try:
            # Get Vehicle object matching VIN number
            vehicle = self.connection.vehicle(self.vin)
            if await vehicle.update(updateType):
                dashboard = vehicle.dashboard(
                    mutable=self.entry.options.get(CONF_MUTABLE),
                    spin=self.entry.options.get(CONF_SPIN),
                )
                self.async_set_updated_data(dashboard.instruments)
                return True
            else:
                _LOGGER.warning("Could not query update from Cupra/Seat API")
                return False
        except Exception as error:
            _LOGGER.warning(f"An error occured in updateCallbackForNotifications while requesting update from Cupra/Seat API: {error}")
            return False

    async def update_only_selected_entity(self, whichInstrument) -> Union[bool, Vehicle]:
        """Update position from My Cupra"""

        # Update vehicle data
        try:
            # Get Vehicle object matching VIN number
            vehicle = self.connection.vehicle(self.vin)
            if whichInstrument.attr == 'position':
                _LOGGER.debug(f"Update for selected entity. Instrument {whichInstrument.attr}")
                rc = await vehicle.get_position()
            elif whichInstrument.attr in ('door_locked', 'door_closed_left_front', 'door_closed_right_front', 'door_closed_left_back', 'door_closed_right_back', 'trunk_locked', 'trunk_closed', 
                                          'hood_closed', 'windows_closed', 'window_closed_left_front', 'window_closed_left_back', 'window_closed_right_front', 'window_closed_right_back'):
                if (vehicle._last_get_statusreport < datetime.now(tz=None) - timedelta(seconds= 30)):
                    _LOGGER.debug(f"Update for selected entity. Instrument {whichInstrument.attr}")
                    rc = await vehicle.get_statusreport()
                else:
                    _LOGGER.info(f"Last API call to update the state of {whichInstrument.attr} less than 30 seconds ago. Not performing a new API call.")
            elif whichInstrument.attr in ('electric_range', 'combustion_range', 'combined_range', 'battery_level', 'fuel_level'):
                _LOGGER.debug(f"Update for selected entity. Instrument {whichInstrument.attr}")
                rc = await vehicle.get_basiccardata()
            else:
                _LOGGER.warning(f"Selective update for instrument {whichInstrument.attr} not implemented yet.")
                return False
            if rc:
                dashboard = vehicle.dashboard(
                    mutable=self.entry.options.get(CONF_MUTABLE),
                    spin=self.entry.options.get(CONF_SPIN),
                )
                self.async_set_updated_data(dashboard.instruments)
                return True
            else:
                _LOGGER.warning(f"Could not query {whichInstrument.attr} from Cupra/Seat API")
                return False
        except Exception as error:
            _LOGGER.warning(f"An error occured while requesting update for {whichInstrument.attr} from Cupra/Seat API: {error}")
            return False
