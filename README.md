# PyCupra - A Home Assistant custom component using the pycupra library to add integration for your Cupra or Seat car 

## This is based on [Farfar/homeassistant-seatconnect](https://github.com/Farfar/homeassistant-seatconnect) modified to support new API of Cupra and Seat
## [Farfar/homeassistant-seatconnect] is based on [lendy007/homeassistant-skodaconnect](https://github.com/lendy007/homeassistant-skodaconnect) modified to support Seat
This integration for Home Assistant will fetch data from My Cupra/My Seat servers related to your Cupra or Seat car.
PyCupra never fetches data directly from car, the car sends updated data to My Cupra/My Seat servers on specific events such as lock/unlock, charging events, climatisation events and when vehicle is parked. The integration will then fetch this data from the servers.
When vehicle actions fails or return with no response, a force refresh might help. This will trigger a "wake up" call from VAG servers to the car.
The scan_interval is how often the integration should fetch data from the servers, if there's no new data from the car then entities won't be updated.

### Supported setups
This integration will only work for your car if you have MyCupra/MySeat functionality. Cars using other third party, semi-official, mobile apps won't work.

The car privacy settings must be set to "Share my position" for full functionality of this integration. Without this setting, if set to "Use my position", the sensors for position (device tracker), requests remaining and parking time might not work reliably or at all. Set to even stricter privacy setting will limit functionality even further.

### What should work, as long as your car supports it (please report if you see something in the app, that you are missing in PyCupra)
- Automatic discovery of enabled functions (API endpoints) based on the (enabled) capabilities of the vehicle
- Charging cable connected
- Charging cable locked
- Charging state, charging power, charging rate and charging time left
- Battery level
- Electric range
- Start/stop charging
- Change charge current (maximum or reduced, current in Ampere for some fully electric models)
- Change target state of charge
- Odometer and service info
- Engine status
- Fuel level, combustion range, combined range, adblue level
- Lock, windows, trunk, hood, sunroof and door status
- Lock and unlock car
- Last trip info and last cycle info (for cars with combustion engine 'last cycle' means 'since refuel')
- Information about status and settings of climatisation and auxiliary heating
- Start/stop Electric climatisation, window_heater
- Start/stop auxiliary heating
- Show, enable/disable and set departure timers, departure profiles and climatisation timers (incl. those for auxiliary heating), respectively (until now, set schedule for departure profiles not tested)
- Position (gps coordinates) and device tracker (showing if the position is lying in one of the zone defined in HA)
- Area Alarm (shows area alarm notifications, if area alarms have been defined and activated in the app; only works with 'Use push notifications' enabled)
- Request wakeup vehicle - this will trigger a wake up call, so the car sends new data and PyCupra reads them (available as switch and as button entity; use what you prefer)
- Request full update - this will trigger, that nearly all vehicle data are reread from the portal (available as switch and as button entity; use what you prefer)
- Model images (downloaded in www/pycupra folder; the image url string is to long for home assistant)
- Send a navigation destination to vehicle

### How to use the area alarms
Using the MyCupra/MySeat app and provided that your car supports it, you can define areas  and activate to get push alerts, if your car enters or leaves a predefined area.
If 'Use push notifications' is enabled in the configuration of PyCupra, then PyCupra will also receive these area alarm notifications and show this alarm with the binary sensor area_alarm. Information about the alarm type and the name of the zone that your car entered of left is shown as attributes of the binary sensor.
The binary sensor is reset after 900 seconds.

You can use the area alarm sensor as trigger for automations e.g. to turn on the light in front of your garage when your car is nearly at home. 

### How to use the model images
The model images of the vehicle are downloaded from the Cupra/Seat cloud and stored in the www/pycupra folder. The names of the model image files are:
- image_{your_VIN}_front.png
- image_{your_VIN}_rear.png
- image_{your_VIN}_side.png
- image_{your_VIN}_top.png
- image_{your_VIN}_rbcFront.png
- image_{your_VIN}_rbcCable.png

You can use these image files for your HA dashboard (e.g. as image for a picture card). Just add the prefix '/local/pycupra' to the file name above and use this as the *image path*. A cropped image of the front view is used as the icon of the vehicle on the Home Assistant map

## Installation

### Installation with HACS
If you have HACS (Home Assistant Community Store) installed, go to the tab HACS on the Home Assistant UI. Enter 'pycupra' in the search field and then select 'PyCupra' from the list below the search field and install it.

### Manual installation
Clone or copy the repository and copy the folder 'homeassistant-pycupra/custom_components/pycupra' into '<config dir>/custom_components'

## Configure

Configuration in configuration.yaml is now deprecated and can interfere with setup of the integration.
To configure the integration, go to Configuration in the side panel of Home Assistant and then select Integrations.
Click on the "ADD INTEGRATION" button in the bottom right corner and search/select pycupra.
Follow the steps and enter the required information. Because of how the data is stored and handled in Home Assistant, there will be one integration per vehicle.
Setup multiple vehicles by adding the integration multiple times. (Not tested yet!)

### Data update concept of PyCupra
The MyCupra/MySeat portal has a per day limitation for the API calls (about 1.500 request per day, including the calls from the MyCupra/MySeat app and other systems that read from the API). If you go above this limit, PyCupra will get not data updates from the API until the portal resets the limit counter at about 02:00 a.m. So the task is to find a good compromise between up-to-date data in HA and the number of API calls.
As some data of your vehicle change faster or more often than others, the reading API calls in PyCupra are divided in three buckets:
- Bucket 1: status of doors and windows, range information and status of charging and climatisation. This bucket uses the INTERVAL setting (poll frequency) described in the configuration options section below. 
- Bucket 2: everything that is not in the buckets 1 or 3 (e.g. mileage, parking position, full charging climatisation information, departure timers/profile, climatisation timers). This bucket is updated about every 20 minutes. (An update for the data in bucket 2 is done, when HA initiates an update (of bucket 1) and the last update of bucket 2 is more than 1100 seconds ago.)
- Bucket 3: the model images. This bucket is updated only every 2 hours. 

You can initiate an update of all data in the buckets 1 and 2 by activating the switch "Request full update".

### Configuration options
The integration options can be changed after setup by clicking on the "CONFIGURE" text on the integration.
The options available are:

* **Poll frequency** The interval (in seconds) that the servers are polled for updated data (only bucket 1 as described above). Please don't use values below 300 seconds, better 600 or 900 seconds.
 
* **Use push notifications** When activated, PyCupra asks the Seat/Cupra portal to send push notifications to PyCupra if the charging status or climatisation status have changed or when the API has finished a request like lock or unlock vehicle, start or stop charging or change departure timers or .... 
 
* **Nightly update reduction** To stay within the daily limitation of API calls, you can activate nightly reduction of updates in the time frame of 22:00 to 05:00 (local time). With activated 'nightly update reduction', the data in the buckets 1 and 2 are updated about once per every 20 minutes in the time frame of 22:00 to 05:00.

Recommendation: Activate 'nightly update reduction' and set poll frequency to 600. If you activate 'use push notifications', a value of 900 is recommended for the poll frequency.

* **S-PIN** The S-PIN for the vehicle. This is optional and is only needed for certain vehicle requests/actions (auxiliary heater, lock etc).

* **Mutable** Select to allow interactions with vehicle, start climatisation etc.

* **Full API debug logging** Enable full debug logging. This will print the full respones from API to homeassistant.log. Only enable for troubleshooting since it will generate a lot of logs.

* **Resources to monitor** Select which resources you wish to monitor for the vehicle.

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
    custom_components.pycupra.button: debug
 ```
* **pycupra.connection:** Set the debug level for the Connection class of the PyCupra library. This handles the GET/SET requests towards the API

* **pycupra.vehicle:** Set the debug level for the Vehicle class of the PyCupra library. One object created for every vehicle in account and stores all data.

* **pycupra.dashboard:** Set the debug level for the Dashboard class of the PyCupra library. A wrapper class between hass component and library.

* **custom_components.pycupra:** Set debug level for the custom component. The communication between hass and library.

* **custom_components.pycupra.XYZ** Sets debug level for individual entity types in the custom component.

## Further help or contributions
For questions, further help or contributions you can join the (V.A.G. Connected Cars) Discord server at https://discord.gg/826X9jEtCh
And I would be glad for help on the translation of the messages and forms of PyCupra to other languages.