# PyCupra - A Home Assistant custom component using the pycupra library to add integration for your Cupra or Seat car 

## This is fork of [Farfar/homeassistant-seatconnect](https://github.com/Farfar/homeassistant-seatconnect) modified to support new API of Cupra and Seat
## This is fork of [lendy007/homeassistant-skodaconnect](https://github.com/lendy007/homeassistant-skodaconnect) modified to support Seat
This integration for Home Assistant will fetch data from My Cupra/My Seat servers related to your Cupra or Seat car.
PyCupra never fetches data directly from car, the car sends updated data to My Cupra/My Seat servers on specific events such as lock/unlock, charging events, climatisation events and when vehicle is parked. The integration will then fetch this data from the servers.
When vehicle actions fails or return with no response, a force refresh might help. This will trigger a "wake up" call from VAG servers to the car.
The scan_interval is how often the integration should fetch data from the servers, if there's no new data from the car then entities won't be updated.

### Supported setups
This integration will only work for your car if you have MyCupra/MySeat functionality. Cars using other third party, semi-official, mobile apps won't work.

The car privacy settings must be set to "Share my position" for full functionality of this integration. Without this setting, if set to "Use my position", the sensors for position (device tracker), requests remaining and parking time might not work reliably or at all. Set to even stricter privacy setting will limit functionality even further.

### What should work (please report if not)
- Automatic discovery of enabled functions (API endpoints).
- Charging plug connected
- Charging plug locked
- Charger connected (external power)
- Battery level
- Electric range
- Start/stop charging
- Start/stop Electric climatisation, window_heater and information
- Change charge current (maximum or reduced)
- Set departure timers
- Odometer and service info
- Fuel level, range, adblue level
- Lock, windows, trunk, hood, sunroof and door status
- Last trip info
- Position - gps coordinates, if vehicle is moving, time parked
- Start/stop auxiliary climatisation for PHEV cars (untested)
- Lock and unlock car
- Device tracker - entity is set to 'not_home' when car is moving
- Trigger data refresh - this will trigger a wake up call so the car sends new data
- Model images (downloaded in www folder; the image url string is to long for home assistant)
- Send a navigation destination to vehicle

## Installation

### Installation with HACS
No supported yet. I'm sorry.

### Manual installation
Clone or copy the repository and copy the folder 'homeassistant-pycupra/custom_components/pycupra' into '<config dir>/custom_components'

## Configure

Configuration in configuration.yaml is now deprecated and can interfere with setup of the integration.
To configure the integration, go to Configuration in the side panel of Home Assistant and then select Integrations.
Click on the "ADD INTEGRATION" button in the bottom right corner and search/select pycupra.
Follow the steps and enter the required information. Because of how the data is stored and handled in Home Assistant, there will be one integration per vehicle.
Setup multiple vehicles by adding the integration multiple times.

### Configuration options
The integration options can be changed after setup by clicking on the "CONFIGURE" text on the integration.
The options available are:

* **Poll frequency** The interval (in seconds) that the servers are polled for updated data(1000 Requests per day limitation by VWGROUP. so min 120 seconds).

* **S-PIN** The S-PIN for the vehicle. This is optional and is only needed for certain vehicle requests/actions (auxiliary heater, lock etc).

* **Mutable** Select to allow interactions with vehicle, start climatisation etc.

* **Full API debug logging** Enable full debug logging. This will print the full respones from API to homeassistant.log. Only enable for troubleshooting since it will generate a lot of logs.

* **Resources to monitor** Select which resources you wish to monitor for the vehicle.

* **Distance/unit conversions** Select if you want to convert distance/units.


## Enable debug logging
For comprehensive debug logging you can add this to your `<config dir>/configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    pycupra.connection: debug
    pycupra.vehicle: debug
    custom_components.pycupra: debug
    custom_components.pycupra.climate: debug
    custom_components.pycupra.lock: debug
    custom_components.pycupra.device_tracker: debug
    custom_components.pycupra.switch: debug
    custom_components.pycupra.binary_sensor: debug
    custom_components.pycupra.sensor: debug
 ```
* **pycupra.connection:** Set the debug level for the Connection class of the PyCupra library. This handles the GET/SET requests towards the API

* **pycupra.vehicle:** Set the debug level for the Vehicle class of the PyCupra library. One object created for every vehicle in account and stores all data.

* **pycupra.dashboard:** Set the debug level for the Dashboard class of the PyCupra library. A wrapper class between hass component and library.

* **custom_components.pycupra:** Set debug level for the custom component. The communication between hass and library.

* **custom_components.pycupra.XYZ** Sets debug level for individual entity types in the custom component.

## Further help or contributions
For questions, further help or contributions you can join the (Skoda Connect) Discord server at https://discord.gg/826X9jEtCh