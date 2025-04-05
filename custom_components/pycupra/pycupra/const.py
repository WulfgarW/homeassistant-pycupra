"""Constants for pycupra library."""

BASE_SESSION = 'https://ola.prod.code.seat.cloud.vwgroup.com'
BASE_AUTH = 'https://identity.vwgroup.io'

# Data used in communication
CLIENT_LIST = {
    'seat': {
        'CLIENT_ID': '99a5b77d-bd88-4d53-b4e5-a539c60694a3@apps_vw-dilab_com',
        'SCOPE': 'openid profile nickname birthdate phone',
        'REDIRECT_URL': 'seat://oauth-callback',
        'TOKEN_TYPES': 'code id_token token'
    },
    'cupra': {
        'CLIENT_ID': '3c756d46-f1ba-4d78-9f9a-cff0d5292d51@apps_vw-dilab_com',
        'CLIENT_SECRET': 'eb8814e641c81a2640ad62eeccec11c98effc9bccd4269ab7af338b50a94b3a2',
        'SCOPE': 'openid profile nickname birthdate phone',
        'REDIRECT_URL': 'cupra://oauth-callback',
        'TOKEN_TYPES': 'code id_token token'
    }
}


XCLIENT_ID = '3c756d46-f1ba-4d78-9f9a-cff0d5292d51@apps_vw-dilab.com' 
XAPPVERSION = '2.5.0'
XAPPNAME = 'com.cupra.mycupra'
USER_AGENT_CUPRA = 'OLACupra/2.5.0 (Android 12; sdk_gphone64_x86_64; Google) Mobile' 
USER_AGENT_SEAT = 'OLASeat/2.5.0 (Android 12; sdk_gphone64_x86_64; Google) Mobile'
APP_URI = 'https://ola.prod.code.seat.cloud.vwgroup.com'

HEADERS_SESSION = {
    'seat': {
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Accept-charset': 'UTF-8',
    'Accept': 'application/json',
    #'X-Client-Id': XCLIENT_ID,
    #'X-App-Version': XAPPVERSION,
    #'X-App-Name': XAPPNAME,
    'User-Agent': USER_AGENT_SEAT
    #'User-ID': '?????', # to be set later
    },
    'cupra': {
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Accept-charset': 'UTF-8',
    'Accept': 'application/json',
    #'X-Client-Id': XCLIENT_ID,
    #'X-App-Version': XAPPVERSION,
    #'X-App-Name': XAPPNAME,
    'User-Agent': USER_AGENT_CUPRA
    #'User-ID': '?????', # to be set later
    }
}

HEADERS_AUTH = {
    'seat': {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': USER_AGENT_SEAT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'x-requested-with': XAPPNAME,
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        #'X-App-Name': XAPPNAME
    },
    'cupra':{
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': USER_AGENT_CUPRA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'x-requested-with': XAPPNAME,
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        #'X-App-Name': XAPPNAME
    }
}

TOKEN_HEADERS = {
    'seat': {
        'Accept': 'application/json',
        'X-Platform': 'Android',
        #'X-Language-Id': 'XX',
        #'X-Country-Id': 'XX',
        #'Accept-Language': 'XX',
        'Accept-Charset': 'UTF-8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip',
        'User-Agent': USER_AGENT_SEAT,
        'app-version': '2.5.0',
        'app-brand': 'seat',
        'app-market': 'android',
        #'User-ID': '?????', # to be set later
        'Authorization': 'Bearer'
    },
    'cupra': {
        'Accept': 'application/json',
        'X-Platform': 'Android',
        #'X-Language-Id': 'XX',
        #'X-Country-Id': 'XX',
        #'Accept-Language': 'XX',
        'Accept-Charset': 'UTF-8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip',
        'User-Agent': USER_AGENT_CUPRA,
        'app-version': '2.5.0',
        'app-brand': 'cupra',
        'app-market': 'android',
        #'User-ID': '?????', # to be set later
        'Authorization': 'Bearer'
    }
}

#ERROR_CODES = {
#    '11': 'Charger not connected'
#}

### API Endpoints below, not yet in use ###
# API AUTH endpoints
AUTH_OIDCONFIG = 'https://identity.vwgroup.io/.well-known/openid-configuration'                     # OpenID configuration
AUTH_TOKEN = 'https://identity.vwgroup.io/oidc/v1/token'                                      # Endpoint for exchanging code for token
AUTH_REFRESH = 'https://ola.prod.code.seat.cloud.vwgroup.com/authorization/api/v1/token'             # Endpoint for token refresh (also used for exchanging code for token for Seat)
AUTH_TOKENKEYS = 'https://identity.vwgroup.io/oidc/v1/keys'                                         # Signing keys for tokens

# API endpoints
API_MBB_STATUSDATA = 'https://customer-profile.vwgroup.io/v3/customers/{self._user_id}/mbbStatusData'
API_PERSONAL_DATA= 'https://customer-profile.vwgroup.io/v3/customers/{self._user_id}/personalData'
API_VEHICLES = '{APP_URI}/v2/users/{self._user_id}/garage/vehicles'                                  # Garage info
API_MYCAR = '{baseurl}/v5/users/{self._user_id}/vehicles/{vin}/mycar'                                # Vehicle status report
API_CHARGING = '{baseurl}/v1/vehicles/{vin}/charging'                                                # Vehicle charging information 
#API_OPERLIST = '{homeregion}/api/rolesrights/operationlist/v3/vehicles/{vin}'                       # API Endpoint for supported operations
#API_CHARGER = 'fs-car/bs/batterycharge/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/charger'                 # Charger data
API_CLIMATER_STATUS = '{baseurl}/v1/vehicles/{vin}/climatisation/status'                             # Climatisation data
API_CLIMATER = '{baseurl}/v2/vehicles/{vin}/climatisation'                         # Climatisation data
API_DEPARTURE_TIMERS = '{baseurl}/v1/vehicles/{vin}/departure-timers'                                 # Departure timers
API_POSITION = '{baseurl}/v1/vehicles/{vin}/parkingposition'                                         # Position data
API_POS_TO_ADDRESS= 'https://maps.googleapis.com/maps/api/directions/json?origin={lat},{lon}&destination={lat},{lon}&traffic_model=best_guess&departure_time=now&language=de&key={apiKeyForGoogle}&mode=driving'
API_TRIP = '{baseurl}/v1/vehicles/{vin}/driving-data/{dataType}?from=1970-01-01T00:00:00Z&to=2099-12-31T09:59:01Z' # Trip statistics (whole history) SHORT/LONG/CYCLIC (WEEK only with from)
API_MILEAGE = '{baseurl}/v1/vehicles/{vin}/mileage'                                                  # Total km etc
API_MAINTENANCE = '{baseurl}/v1/vehicles/{vin}/maintenance'                                          # Inspection information
API_MEASUREMENTS = '{baseurl}/v1/vehicles/{vin}/measurements/engines'                                # ???
API_STATUS = '{baseurl}/v2/vehicles/{vin}/status'                                                    # Status information like locks and windows
API_WARNINGLIGHTS = '{baseurl}/v3/vehicles/{vin}/warninglights'                                      # ???
API_SHOP = '{baseurl}/v1/shop/vehicles/{vin}/articles'                                               # ???
#API_ACTION = '{baseurl}/v1/vehicles/{vin}/{action}/requests/{command}'                               # Actions (e.g. ActionCharge="charging", ActionChargeStart="start",ActionChargeStop="stop")
API_RELATION_STATUS = '{baseurl}/v1/users/{self._user_id}/vehicles/{vin}/relation-status'            # ???
API_INVITATIONS = '{baseurl}/v1/user/{self._user_id}/invitations'                                    # ???
API_CAPABILITIES = '{APP_URI}/v1/user/{self._user_id}/vehicle/{vin}/capabilities'                    # ???
#API_CAPABILITIES_MANAGEMENT = '{API_CAPABILITIES}/management'                                        # ???
API_IMAGE = '{baseurl}/v1/vehicles/{vin}/renders'
API_HONK_AND_FLASH = '{baseurl}//v1/vehicles/{vin}/honk-and-flash'
API_ACCESS = '{baseurl}//v1/vehicles/{vin}/access/{action}'                                          # to lock or unlock vehicle
API_REQUESTS = '{baseurl}/vehicles/{vin}/{capability}/requests'
API_REFRESH = '{baseurl}/v1/vehicles/{vin}/vehicle-wakeup/request'
API_SECTOKEN = '{baseurl}/v2/users/{self._user_id}/spin/verify'
API_DESTINATION = '{baseurl}/v1/users/vehicles/{vin}/destination'
API_LITERALS= '{APP_URI}/v1/content/apps/my-cupra/literals/{language}'                               # Message texts in different langauages, e.g. 'en_GB'

# Still to analyse if needed
#'{baseurl}/settings/api/v1?vin={vin}&vehicle-model=LeonST&region=US&enrolment-country=DE&platform=MOD3'
#'{baseurl}/v1/users/{self._user_id}/vin/{vin}/terms-and-conditions'
#'{baseurl}/v2/subscriptions'
#'{baseurl}/v1/users/{self._user_id}/vehicles/{vin}/leads/history'
#'{baseurl}/v1/users/{self._user-id}/vehicles/{vin}/consents/xxcryptickeyxxx?locale=en_DE' #{"userId":"xxxxxxx","locale":"en_DE","error":{"title":"Consent failed to load.","detail":"CUPRAApp_ME3_Vehicle_VehiclePermissions_MainViewAccepted_Low_Type1_Wrong"}}

API_CONNECTION= '{APP_URI}/vehicles/{vin}/connection'
#API_CONSENTS='{APP_URI}/v1/users/{self._user_id}/consents'
API_PSP='{baseurl}/v2/users/{self._user_id}/vehicles/{vin}/psp'     # primary service provider (Werkstatt)
API_USER_INFO= 'https://identity-userinfo.vwgroup.io/oidc/userinfo' #{"sub":"xxx","name":"xxx","given_name":"xxx","family_name":"xxx","nickname":"xxx","email":"###","email_verified":true,"birthdate":"###","updated_at":123456789,"picture":"https://customer-pictures.vwgroup.io/v1/###/profile-picture"}

PUBLIC_MODEL_IMAGES_SERVER = 'prod-ola-public-bucket.s3.eu-central-1.amazonaws.com'                      # non-indivdual model images are on this server

# API endpoints for status
REQ_STATUS = {
    'climatisation': 'fs-car/bs/climatisation/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/climater/actions/{id}',
    'batterycharge': 'fs-car/bs/batterycharge/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/charger/actions/{id}',
    'departuretimer': 'fs-car/bs/departuretimer/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/timer/actions/{id}',
    'vsr': 'fs-car/bs/vsr/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/requests/{id}/jobstatus',
    'default': 'fs-car/bs/{section}/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/requests/{id}/status'
}
