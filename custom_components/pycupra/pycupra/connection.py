#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Communicate with the My Cupra portal."""
"""First fork from https://github.com/robinostlund/volkswagencarnet where it was modified to support also Skoda Connect"""
"""Then forked from https://github.com/lendy007/skodaconnect for adaptation to Seat Connect"""
"""Then forked from https://github.com/Farfar/seatconnect for adaptation to the new API of My Cupra and My Seat"""
import re
import os
import json
import logging
import asyncio
import hashlib
import jwt
import string
import secrets
import xmltodict

from sys import version_info, argv
from datetime import timedelta, datetime, timezone
from urllib.parse import urljoin, parse_qs, urlparse, urlencode
from json import dumps as to_json
from jwt.exceptions import ExpiredSignatureError
import aiohttp
from bs4 import BeautifulSoup
from base64 import b64decode, b64encode
from .__version__ import __version__ as lib_version
from .utilities import read_config, json_loads
from .vehicle import Vehicle
from .exceptions import (
    SeatConfigException,
    SeatAuthenticationException,
    SeatAccountLockedException,
    SeatTokenExpiredException,
    SeatException,
    SeatEULAException,
    SeatThrottledException,
    SeatLoginFailedException,
    SeatInvalidRequestException,
    SeatRequestInProgressException,
    SeatServiceUnavailable
)

from requests_oauthlib import OAuth2Session
import base64
from oauthlib.oauth2.rfc6749.parameters import parse_authorization_code_response, parse_token_response, prepare_grant_uri

from aiohttp import ClientSession, ClientTimeout
from aiohttp.hdrs import METH_GET, METH_POST, METH_PUT

from .const import (
    HEADERS_SESSION,
    HEADERS_AUTH,
    TOKEN_HEADERS,
    BASE_SESSION,
    BASE_AUTH,
    CLIENT_LIST,
    XCLIENT_ID,
    XAPPVERSION,
    XAPPNAME,
    AUTH_OIDCONFIG,
    AUTH_TOKEN,
    AUTH_TOKENKEYS,
    AUTH_REFRESH,
    APP_URI,
    API_MBB_STATUSDATA,
    API_PERSONAL_DATA,
    API_USER_INFO,
    API_CONNECTION,
    API_PSP,
    API_VEHICLES,
    API_MYCAR,
    API_STATUS,
    API_CHARGING,
    API_POSITION,
    API_POS_TO_ADDRESS,
    API_TRIP,
    API_CLIMATER_STATUS,
    API_CLIMATER,
    API_DEPARTURE_TIMERS,
    API_MILEAGE,
    API_CAPABILITIES,
    #API_CAPABILITIES_MANAGEMENT,
    API_MAINTENANCE,
    API_WARNINGLIGHTS,
    API_MEASUREMENTS,
    API_RELATION_STATUS,
    API_INVITATIONS,
    #API_ACTION,
    API_IMAGE,
    API_HONK_AND_FLASH,
    API_ACCESS,
    API_SECTOKEN,
    API_REQUESTS,
    API_REFRESH,
    API_DESTINATION,

    PUBLIC_MODEL_IMAGES_SERVER,
)

version_info >= (3, 0) or exit('Python 3 required')

_LOGGER = logging.getLogger(__name__)
BRAND_CUPRA = 'cupra'
TIMEOUT = timedelta(seconds=90)

class Connection:
    """ Connection to Connect services """
  # Init connection class
    def __init__(self, session, brand='cupra', username='', password='', fulldebug=False, **optional):
        """ Initialize """
        self._session = session
        self._lock = asyncio.Lock()
        self._session_fulldebug = fulldebug
        self._session_headers = HEADERS_SESSION.get(brand).copy()
        self._session_base = BASE_SESSION
        self._session_auth_headers = HEADERS_AUTH.copy()
        self._session_token_headers = TOKEN_HEADERS.copy()
        self._session_cookies = ""
        self._session_nonce = self._getNonce()
        self._session_state = self._getState()

        self._session_auth_ref_url = BASE_SESSION
        self._session_spin_ref_url = BASE_SESSION
        self._session_first_update = False
        self._session_auth_brand = brand
        self._session_auth_username = username
        self._session_auth_password = password
        self._session_tokens = {}

        self._vehicles = []
        self._userData = {}

        _LOGGER.info(f'Init PyCupra library, version {lib_version}')
        _LOGGER.debug(f'Using service {self._session_base}')


    def _clear_cookies(self):
        self._session._cookie_jar._cookies.clear()
        self._session_cookies = ''

    def _getNonce(self):
        chars = string.ascii_letters + string.digits
        text = ''.join(secrets.choice(chars) for i in range(10))
        sha256 = hashlib.sha256()
        sha256.update(text.encode())
        return (b64encode(sha256.digest()).decode('utf-8')[:-1])

    def _getState(self):
        return self._getNonce()

    def readTokenFile(self, brand):
        try:
            if os.path.isfile(self._tokenFile):
                with open(self._tokenFile, "r") as f:
                    tokenString=f.read()
                tokens=json.loads(tokenString)
                self._session_tokens[brand]=tokens
                self._user_id=tokens['user_id']
                return True
            _LOGGER.info('No token file present. readTokenFile() returns False.')
            return False
        except:
            _LOGGER.warning('readTokenFile() not successful.')
            return False

    def writeTokenFile(self, brand):
        if hasattr(self, '_tokenfile'):
            _LOGGER.info('No token file name provided. Cannot write tokens to file.')
            return False
        self._session_tokens[brand]['user_id']=self._user_id
        try:
            with open(self._tokenFile, "w") as f:
                f.write(json.dumps(self._session_tokens[brand]))
            return True
        except Exception as e:
            _LOGGER.warning(f'writeTokenFile() not successful. Error: {e}')
            return False

    def deleteTokenFile(self):
        if hasattr(self, '_tokenfile'):
            _LOGGER.debug('No token file name provided. Cannot delete token file.')
            return False
        try:
            os.remove(self._tokenFile)
            _LOGGER.info(f'Deleted token file.')
            return True
        except Exception as e:
            _LOGGER.warning(f'deleteTokenFile() not successful. Error: {e}')
            return False

    def writeImageFile(self, imageName, imageData, imageDict):
        try:
            with open(f'./www/image_{imageName}.png', "wb") as f:
                f.write(imageData)
            imageDict[imageName]=f'/local/image_{imageName}.png'
            return True
        except:
            _LOGGER.warning('writeImageFile() not successful. Ignoring this problem.')
            return False

  # API login/logout/authorization
    async def doLogin(self,**data):
        """Login method, clean login or use token from file and refresh it"""
        #if len(self._session_tokens) > 0:
        #    _LOGGER.info('Revoking old tokens.')
        #    try:
        #        await self.logout()
        #    except:
        #        pass
        _LOGGER.info('doLogin() first tries to read tokens from file and to refresh them.')

        # Remove cookies and re-init session
        self._clear_cookies()
        self._vehicles.clear()
        self._session_tokens = {}
        self._session_headers = HEADERS_SESSION.get(self._session_auth_brand).copy()
        self._session_auth_headers = HEADERS_AUTH.copy()
        self._session_nonce = self._getNonce()
        self._session_state = self._getState()

        if data.get('apiKey',None)!=None:
            self._googleApiKey=data.get('apiKey')
        if data.get('tokenFile',None)!=None:
            self._tokenFile=data.get('tokenFile')
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self.readTokenFile, self._session_auth_brand)
            if result:
                rc=await self.refresh_token(self._session_auth_brand)
                if rc:
                    _LOGGER.info('Successfully read tokens from file and refreshed them.')
                    return True
        _LOGGER.info('Initiating new login with user name and password.')
        return await self._authorize(self._session_auth_brand)

    async def _authorize(self, client=BRAND_CUPRA):
        """"Login" function. Authorize a certain client type and get tokens."""
        # Helper functions
        def extract_csrf(req):
            return re.compile('<meta name="_csrf" content="([^"]*)"/>').search(req).group(1)

        def extract_guest_language_id(req):
            return req.split('_')[1].lower()

        # Login/Authorization starts here
        try:
            #self._session_headers = HEADERS_SESSION.get(client).copy()
            #self._session_auth_headers = HEADERS_AUTH.copy()

            _LOGGER.debug(f'Starting authorization process for client {client}')
            req = await self._session.get(
                url=AUTH_OIDCONFIG
            )
            if req.status != 200:
                _LOGGER.debug(f'Get request to {AUTH_OIDCONFIG} was not successful. Response: {req}')
                return False
            response_data =  await req.json()
            authorizationEndpoint = response_data['authorization_endpoint']
            authissuer = response_data['issuer']
            oauthClient = OAuth2Session(client_id=CLIENT_LIST[client].get('CLIENT_ID'), scope=CLIENT_LIST[client].get('SCOPE'), redirect_uri=CLIENT_LIST[client].get('REDIRECT_URL'))
            code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8')
            code_verifier = re.sub('[^a-zA-Z0-9]+', '', code_verifier)
            code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
            code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
            code_challenge = code_challenge.replace("=", "")
            authorization_url, state = oauthClient.authorization_url(authorizationEndpoint, code_challenge=code_challenge, code_challenge_method='S256', 
                                                                        nonce=self._session_nonce, state=self._session_state)

            # Get authorization page (login page)
            if self._session_fulldebug:
                _LOGGER.debug(f'Get authorization page: "{authorization_url}"')
            try:
                req = await self._session.get(
                    url=authorization_url,
                        headers=self._session_auth_headers.get(client),
                        allow_redirects=False
                    )
                if req.headers.get('Location', False):
                    ref = req.headers.get('Location', '')
                    if 'error' in ref:
                        error = parse_qs(urlparse(ref).query).get('error', '')[0]
                        if 'error_description' in ref:
                            error = parse_qs(urlparse(ref).query).get('error_description', '')[0]
                            _LOGGER.info(f'Unable to login, {error}')
                        else:
                            _LOGGER.info(f'Unable to login.')
                        raise SeatException(error)
                    else:
                        if self._session_fulldebug:
                            _LOGGER.debug(f'Got authorization endpoint: "{ref}"')
                        req = await self._session.get(
                            url=ref,
                            headers=self._session_auth_headers.get(client),
                            allow_redirects=False
                        )
                else:
                    _LOGGER.warning(f'Unable to fetch authorization endpoint')
                    raise SeatException('Missing "location" header')
            except (SeatException):
                raise
            except Exception as error:
                _LOGGER.warning(f'Failed to get authorization endpoint. {error}')
                raise SeatException(error)

            # If we need to sign in (first token)
            if 'signin-service' in ref:
                _LOGGER.debug("Got redirect to signin-service")
                location = await self._signin_service(req, authissuer, authorizationEndpoint, client)
            else:
                # We are already logged on, shorter authorization flow
                location = req.headers.get('Location', None)

            # Follow all redirects until we reach the callback URL
            try:
                maxDepth = 10
                while not location.startswith(CLIENT_LIST[client].get('REDIRECT_URL')):
                    if location is None:
                        raise SeatException('Login failed')
                    if 'error' in location:
                        error = parse_qs(urlparse(location).query).get('error', '')[0]
                        if error == 'login.error.throttled':
                            timeout = parse_qs(urlparse(location).query).get('enableNextButtonAfterSeconds', '')[0]
                            raise SeatAccountLockedException(f'Account is locked for another {timeout} seconds')
                        elif error == 'login.errors.password_invalid':
                            raise SeatAuthenticationException('Invalid credentials')
                        else:
                            _LOGGER.warning(f'Login failed: {error}')
                        raise SeatLoginFailedException(error)
                    if 'terms-and-conditions' in location:
                        raise SeatEULAException('The terms and conditions must be accepted first at your local SEAT/Cupra site, e.g. "https://cupraofficial.se/"')
                    if 'user_id' in location: # Get the user_id which is needed for some later requests
                        self._user_id=parse_qs(urlparse(location).query).get('user_id')[0]
                        _LOGGER.debug('Got user_id: %s' % self._user_id)
                    if self._session_fulldebug:
                        _LOGGER.debug(f'Following redirect to "{location}"')
                    response = await self._session.get(
                        url=location,
                        headers=self._session_auth_headers.get(client),
                        allow_redirects=False
                    )
                    if response.headers.get('Location', False) is False:
                        _LOGGER.debug(f'Unexpected response: {await req.text()}')
                        raise SeatAuthenticationException('User appears unauthorized')
                    location = response.headers.get('Location', None)
                    # Set a max limit on requests to prevent forever loop
                    maxDepth -= 1
                    if maxDepth == 0:
                        raise SeatException('Too many redirects')
            except (SeatException, SeatEULAException, SeatAuthenticationException, SeatAccountLockedException, SeatLoginFailedException):
                raise
            except Exception as e:
                # If we get an unhandled exception it should be because we can't redirect to the APP_URI URL and thus we have our auth code
                if 'code' in location:
                    if self._session_fulldebug:
                        _LOGGER.debug('Got code: %s' % location)
                    pass
                else:
                    _LOGGER.debug(f'Exception occured while logging in.')
                    raise SeatLoginFailedException(e)

            _LOGGER.debug('Received authorization code, exchange for tokens.')
            # Extract code and tokens
            auth_code = parse_qs(urlparse(location).query).get('code')[0]
            # Save access, identity and refresh tokens according to requested client"""
            if client=='cupra':
                # oauthClient.fetch_token() does not work in home assistant, using POST request instead
                #token_data= oauthClient.fetch_token(token_url=AUTH_TOKEN,  
                #                       client_id=CLIENT_LIST[client].get('CLIENT_ID'), client_secret=CLIENT_LIST[client].get('CLIENT_SECRET'), authorization_response=location, 
                #                       code_verifier=code_verifier, code=auth_code)
                data = {
                        'redirect_uri': CLIENT_LIST[client].get('REDIRECT_URL'),
                        'client_id': CLIENT_LIST[client].get('CLIENT_ID'),
                        'client_secret': CLIENT_LIST[client].get('CLIENT_SECRET'), 
                        'authorization_response': location,
                        'code': auth_code,
                        'code_verifier': code_verifier,
                        'grant_type': 'authorization_code'
                        }
                req = await self._session.post(
                    url=AUTH_TOKEN,
                    data = data,
                    headers=self._session_auth_headers.get(client),
                    allow_redirects=False
                    )
                token_data = await req.json()
            else:
                data = {
                        'redirect_uri': CLIENT_LIST[client].get('REDIRECT_URL'),
                        'client_id': CLIENT_LIST[client].get('CLIENT_ID'),
                        'code': auth_code,
                        'code_verifier': code_verifier,
                        'grant_type': 'authorization_code'
                        }
                req = await self._session.post(
                    url=AUTH_REFRESH,
                    data = data,
                    headers=self._session_auth_headers.get(client),
                    allow_redirects=False
                    )
                token_data = await req.json()
            self._session_tokens[client] = {}
            for key in token_data:
                if '_token' in key:
                    self._session_tokens[client][key] = token_data[key]
            if 'error' in self._session_tokens[client]:
                error = self._session_tokens[client].get('error', '')
                if 'error_description' in self._session_tokens[client]:
                    error_description = self._session_tokens[client].get('error_description', '')
                    raise SeatException(f'{error} - {error_description}')
                else:
                    raise SeatException(error)
            if self._session_fulldebug:
                for key in self._session_tokens.get(client, {}):
                    if 'token' in key:
                        _LOGGER.debug(f'Got {key} for client {CLIENT_LIST[client].get("CLIENT_ID","")}, token: "{self._session_tokens.get(client, {}).get(key, None)}"')
            # Verify token, warn if problems are found
            verify = await self.verify_token(self._session_tokens[client].get('id_token', ''))
            if verify is False:
                _LOGGER.warning(f'Token for {client} is invalid!')
            elif verify is True:
                _LOGGER.debug(f'Token for {client} verified OK.')
            else:
                _LOGGER.warning(f'Token for {client} could not be verified, verification returned {verify}.')
            loop = asyncio.get_running_loop()
            rt = await loop.run_in_executor(None, self.writeTokenFile, client)
        except (SeatEULAException):
            _LOGGER.warning('Login failed, the terms and conditions might have been updated and need to be accepted. Login to  your local SEAT/Cupra site, e.g. "https://cupraofficial.se/" and accept the new terms before trying again')
            raise
        except (SeatAccountLockedException):
            _LOGGER.warning('Your account is locked, probably because of too many incorrect login attempts. Make sure that your account is not in use somewhere with incorrect password')
            raise
        except (SeatAuthenticationException):
            _LOGGER.warning('Invalid credentials or invalid configuration. Make sure you have entered the correct credentials')
            raise
        except (SeatException):
            _LOGGER.error('An API error was encountered during login, try again later')
            raise
        except (TypeError):
            _LOGGER.warning(f'Login failed for {self._session_auth_username}. The server might be temporarily unavailable, try again later. If the problem persists, verify your account at your local SEAT/Cupra site, e.g. "https://cupraofficial.se/"')
        except Exception as error:
            _LOGGER.error(f'Login failed for {self._session_auth_username}, {error}')
            return False
        return True

    async def _signin_service(self, html, authissuer, authorizationEndpoint, client=BRAND_CUPRA):
        """Method to signin to Connect portal."""
        # Extract login form and extract attributes
        try:
            response_data = await html.text()
            responseSoup = BeautifulSoup(response_data, 'html.parser')
            form_data = dict()
            if responseSoup is None:
                raise SeatLoginFailedException('Login failed, server did not return a login form')
            for t in responseSoup.find('form', id='emailPasswordForm').find_all('input', type='hidden'):
                if self._session_fulldebug:
                    _LOGGER.debug(f'Extracted form attribute: {t["name"], t["value"]}')
                form_data[t['name']] = t['value']
            form_data['email'] = self._session_auth_username
            pe_url = authissuer+responseSoup.find('form', id='emailPasswordForm').get('action')
        except Exception as e:
            _LOGGER.error('Failed to extract user login form.')
            raise

        # POST email
        self._session_auth_headers[client]['Referer'] = authorizationEndpoint
        self._session_auth_headers[client]['Origin'] = authissuer
        _LOGGER.debug(f"Start authorization for user {self._session_auth_username}")
        req = await self._session.post(
            url = pe_url,
            headers = self._session_auth_headers.get(client),
            data = form_data
        )
        if req.status != 200:
            raise SeatException('Authorization request failed')
        try:
            response_data = await req.text()
            responseSoup = BeautifulSoup(response_data, 'html.parser')
            pwform = {}
            credentials_form = responseSoup.find('form', id='credentialsForm')
            all_scripts = responseSoup.find_all('script', {'src': False})
            if credentials_form is not None:
                _LOGGER.debug('Found HTML credentials form, extracting attributes')
                for t in credentials_form.find_all('input', type='hidden'):
                    if self._session_fulldebug:
                        _LOGGER.debug(f'Extracted form attribute: {t["name"], t["value"]}')
                    pwform[t['name']] = t['value']
                    form_data = pwform
                    post_action = responseSoup.find('form', id='credentialsForm').get('action')
            elif all_scripts is not None:
                _LOGGER.debug('Found dynamic credentials form, extracting attributes')
                pattern = re.compile("templateModel: (.*?),\n")
                for sc in all_scripts:
                    if(pattern.search(sc.string)):
                        import json
                        data = pattern.search(sc.string)
                        jsondata = json.loads(data.groups()[0])
                        _LOGGER.debug(f'JSON: {jsondata}')
                        if not jsondata.get('hmac', False):
                            raise SeatLoginFailedException('Failed to extract login hmac attribute')
                        if not jsondata.get('postAction', False):
                            raise SeatLoginFailedException('Failed to extract login post action attribute')
                        if jsondata.get('error', None) is not None:
                            raise SeatLoginFailedException(f'Login failed with error: {jsondata.get("error", None)}')
                        form_data['hmac'] = jsondata.get('hmac', '')
                        post_action = jsondata.get('postAction')
            else:
                raise SeatLoginFailedException('Failed to extract login form data')
            form_data['password'] = self._session_auth_password
        except (SeatLoginFailedException) as e:
            raise
        except Exception as e:
            raise SeatAuthenticationException("Invalid username or service unavailable")

        # POST password
        self._session_auth_headers[client]['Referer'] = pe_url
        self._session_auth_headers[client]['Origin'] = authissuer
        _LOGGER.debug(f"Finalizing login")

        client_id = CLIENT_LIST[client].get('CLIENT_ID')
        pp_url = authissuer+'/'+post_action
        if not 'signin-service' in pp_url or not client_id in pp_url:
            pp_url = authissuer+'/signin-service/v1/'+client_id+"/"+post_action

        if self._session_fulldebug:
            _LOGGER.debug(f'Using login action url: "{pp_url}"')
        req = await self._session.post(
            url=pp_url,
            headers=self._session_auth_headers.get(client),
            data = form_data,
            allow_redirects=False
        )
        return req.headers.get('Location', None)

    async def terminate(self):
        """Log out from connect services"""
        await self.logout()

    async def logout(self):
        """Logout, revoke tokens."""
        _LOGGER.info(f'Initiating logout.')
        self._session_headers.pop('Authorization', None)
        self._session_headers.pop('tokentype', None)
        self._session_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        for client in self._session_tokens:
            # Ignore identity tokens
            for token_type in (
                token_type
                for token_type in self._session_tokens[client]
                if token_type in ['refresh_token', 'access_token']
            ):
                self._session_tokens[client][token_type] = None
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.deleteTokenFile,)

  # HTTP methods to API
    async def get(self, url, vin=''):
        """Perform a HTTP GET."""
        try:
            response = await self._request(METH_GET, url)
            return response
        except aiohttp.client_exceptions.ClientResponseError as error:
            data = {
                'status_code': error.status,
                'error': error.code,
                'error_description': error.message,
                'response_headers': error.headers,
                'request_info': error.request_info
            }
            if error.status == 401:
                _LOGGER.warning('Received "Unauthorized" while fetching data.\nThis can occur if tokens expired or refresh service is unavailable.')
            elif error.status == 400:
                _LOGGER.error('Received "Bad Request" from server.\nThe request might be malformed or not implemented correctly for this vehicle.')
            elif error.status == 412:
                _LOGGER.debug('Received "Pre-condition failed".\nService might be temporarily unavailable.')
            elif error.status == 500:
                _LOGGER.info('Received "Internal server error".\nThe service is temporarily unavailable.')
            elif error.status == 502:
                _LOGGER.info('Received "Bad gateway".\nEither the endpoint is temporarily unavailable or not supported for this vehicle.')
            elif 400 <= error.status <= 499:
                _LOGGER.error('Received unhandled error indicating client-side problem.\nRestart or try again later.')
            elif 500 <= error.status <= 599:
                _LOGGER.error('Received unhandled error indicating server-side problem.\nThe service might be temporarily unavailable.')
            else:
                _LOGGER.error('Received unhandled error while requesting API endpoint.')
            _LOGGER.debug(f'HTTP request information: {data}')
            return data
        except Exception as e:
            _LOGGER.debug(f'Got non HTTP related error: {e}')

    async def post(self, url, **data):
        """Perform a HTTP POST."""
        if data:
            return await self._request(METH_POST, url, **data)
        else:
            return await self._request(METH_POST, url)

    async def _request(self, method, url, **kwargs):
        """Perform a HTTP query"""
        if self._session_fulldebug:
            _LOGGER.debug(f'HTTP {method} "{url}"')
        async with self._session.request(
            method,
            url,
            headers=self._session_headers if (PUBLIC_MODEL_IMAGES_SERVER not in url) else {}, # Set headers to {} when reading from PUBLIC_MODEL_IMAGES_SERVER
            timeout=ClientTimeout(total=TIMEOUT.seconds),
            cookies=self._session_cookies,
            raise_for_status=False,
            **kwargs
        ) as response:
            response.raise_for_status()

            # Update cookie jar
            if self._session_cookies != '':
                self._session_cookies.update(response.cookies)
            else:
                self._session_cookies = response.cookies

            try:
                if response.status == 204:
                    res = {'status_code': response.status}
                elif response.status >= 200 or response.status <= 300:
                    # If this is a revoke token url, expect Content-Length 0 and return
                    if int(response.headers.get('Content-Length', 0)) == 0 and 'revoke' in url:
                        if response.status == 200:
                            return True
                        else:
                            return False
                    else:
                        if 'xml' in response.headers.get('Content-Type', ''):
                            res = xmltodict.parse(await response.text())
                        elif 'image/png'  in response.headers.get('Content-Type', ''):
                            res = await response.content.read()
                        else:
                            res = await response.json(loads=json_loads)
                else:
                    res = {}
                    _LOGGER.debug(f'Not success status code [{response.status}] response: {response}')
                if 'X-RateLimit-Remaining' in response.headers:
                    res['rate_limit_remaining'] = response.headers.get('X-RateLimit-Remaining', '')
            except Exception as e:
                res = {}
                _LOGGER.debug(f'Something went wrong [{response.status}] response: {response}, error: {e}')
                return res

            if self._session_fulldebug:
                if 'image/png'  in response.headers.get('Content-Type', ''):
                    _LOGGER.debug(f'Request for "{url}" returned with status code [{response.status}]. Not showing response for Content-Type image/png.')
                else:
                    _LOGGER.debug(f'Request for "{url}" returned with status code [{response.status}], response: {res}')
            else:
                _LOGGER.debug(f'Request for "{url}" returned with status code [{response.status}]')
            return res

    async def _data_call(self, query, **data):
        """Function for POST actions with error handling."""
        try:
            response = await self.post(query, **data)
            _LOGGER.debug(f'Data call returned: {response}')
            return response
        except aiohttp.client_exceptions.ClientResponseError as error:
            _LOGGER.debug(f'Request failed. Data: {data}, HTTP request headers: {self._session_headers}')
            if error.status == 401:
                _LOGGER.error('Unauthorized')
            elif error.status == 400:
                _LOGGER.error(f'Bad request')
            elif error.status == 429:
                _LOGGER.warning('Too many requests. Further requests can only be made after the end of next trip in order to protect your vehicles battery.')
                return 429
            elif error.status == 500:
                _LOGGER.error('Internal server error, server might be temporarily unavailable')
            elif error.status == 502:
                _LOGGER.error('Bad gateway, this function may not be implemented for this vehicle')
            else:
                _LOGGER.error(f'Unhandled HTTP exception: {error}')
            #return False
        except Exception as error:
            _LOGGER.error(f'Failure to execute: {error}')
        return False

  # Class get data functions
    async def update_all(self):
        """Update status."""
        try:
            # Get all Vehicle objects and update in parallell
            update_list = []
            for vehicle in self.vehicles:
                if vehicle.vin not in update_list:
                    _LOGGER.debug(f'Adding {vehicle.vin} for data refresh')
                    update_list.append(vehicle.update())
                else:
                    _LOGGER.debug(f'VIN {vehicle.vin} is already queued for data refresh')

            # Wait for all data updates to complete
            if len(update_list) == 0:
                _LOGGER.info('No vehicles in account to update')
            else:
                _LOGGER.debug('Calling update function for all vehicles')
                await asyncio.gather(*update_list)
            return True
        except (IOError, OSError, LookupError, Exception) as error:
            _LOGGER.warning(f'An error was encountered during interaction with the API: {error}')
        except:
            raise
        return False

    async def get_userData(self):
        """Fetch user profile."""
        await self.set_token(self._session_auth_brand)
        userData={}
        #API_PERSONAL_DATA liefert fast das gleiche wie API_USER_INFO aber etwas weniger
        try:
            response = await self.get(eval(f"f'{API_PERSONAL_DATA}'"))
            if response.get('nickname'):
                userData= response
            else:
                _LOGGER.debug('Could not retrieve profile information')
        except:
            _LOGGER.debug('Could not fetch personal information.')

        try:
            response = await self.get(eval(f"f'{API_USER_INFO}'"))
            if response.get('name'):
                userData = response
            else:
                _LOGGER.debug('Could not retrieve profile information')
        except:
            _LOGGER.debug('Could not fetch personal information.')
        self._userData=userData
        return userData

    async def get_vehicles(self):
        """Fetch vehicle information from user profile."""
        api_vehicles = []
        # Check if user needs to update consent
        try:
            await self.set_token(self._session_auth_brand)
            _LOGGER.debug('Achtung! getConsentInfo auskommentiert')
            response = await self.get(eval(f"f'{API_MBB_STATUSDATA}'"))
            if response.get('profileCompleted','incomplete'):
                if response.get('profileCompleted',False):
                    _LOGGER.debug('User consent is valid, no missing information for profile')
                else:
                    _LOGGER.debug('Profile incomplete. Please visit the web portal')
            else:
                _LOGGER.debug('Could not retrieve profile information')
            """consent = await self.getConsentInfo()
            if isinstance(consent, dict):
                _LOGGER.debug(f'Consent returned {consent}')
                if 'status' in consent.get('mandatoryConsentInfo', []):
                    if consent.get('mandatoryConsentInfo', [])['status'] != 'VALID':
                        _LOGGER.error(f'The user needs to update consent for {consent.get("mandatoryConsentInfo", [])["id"]}. If problems are encountered please visit the web portal first and accept terms and conditions.')
                elif len(consent.get('missingMandatoryFields', [])) > 0:
                    _LOGGER.error(f'Missing mandatory field for user: {consent.get("missingMandatoryFields", [])[0].get("name", "")}. If problems are encountered please visit the web portal first and accept terms and conditions.')
                else:
                    _LOGGER.debug('User consent is valid, no missing information for profile')
            else:
                _LOGGER.debug('Could not retrieve consent information')"""
        except:
            _LOGGER.debug('Could not fetch consent information. If problems are encountered please visit the web portal first and make sure that no new terms and conditions need to be accepted.')

        # Fetch vehicles
        try:
            legacy_vehicles = await self.get(eval(f"f'{API_VEHICLES}'"))
            if legacy_vehicles.get('vehicles', False):
                _LOGGER.debug('Found vehicle(s) associated with account.')
                for vehicle in legacy_vehicles.get('vehicles'):
                    vin = vehicle.get('vin', '')
                    response = await self.get(eval(f"f'{API_CAPABILITIES}'"))
                    #self._session_headers['Accept'] = 'application/json'
                    if response.get('capabilities', False):
                        vehicle["capabilities"]=response.get('capabilities')
                    else:
                        _LOGGER.warning(f"Failed to aquire capabilities information about vehicle with VIN {vehicle}")
                    response = await self.get(eval(f"f'{API_CONNECTION}'"))
                    #self._session_headers['Accept'] = 'application/json'
                    if response.get('connection', False):
                        vehicle["connectivities"]=response.get('connection')
                    else:
                        _LOGGER.warning(f"Failed to aquire connection information about vehicle with VIN {vehicle}")
                    api_vehicles.append(vehicle)
        except:
            raise

        # If neither API returns any vehicles, raise an error
        if len(api_vehicles) == 0:
            raise SeatConfigException("No vehicles were found for given account!")
        # Get vehicle connectivity information
        else:
            try:
                for vehicle in api_vehicles:
                    _LOGGER.debug(f'Checking vehicle {vehicle}')
                    vin = vehicle.get('vin', '')
                    #for service in vehicle.get('connectivities', []):
                    #    if isinstance(service, str):
                    #        connectivity.append(service)
                    #    elif isinstance(service, dict):
                    #        connectivity.append(service.get('type', ''))

                    properties={}
                    for key in vehicle:
                        if not(key in {'capabilities', 'vin', 'specifications', 'connectivities'}):
                            properties[key]=vehicle.get(key)

                    newVehicle = {
                        'vin': vin,
                        'connectivities': vehicle.get('connectivities'),
                        'capabilities': vehicle.get('capabilities'),
                        'specification': vehicle.get('specifications'),
                        'properties': properties,
                    }
                    # Check if object already exist
                    _LOGGER.debug(f'Check if vehicle exists')
                    if self.vehicle(vin) is not None:
                        _LOGGER.debug(f'Vehicle with VIN number {vin} already exist.')
                        car = Vehicle(self, newVehicle)
                        if not car == self.vehicle(newVehicle):
                            _LOGGER.debug(f'Updating {newVehicle} object')
                            self._vehicles.pop(newVehicle)
                            self._vehicles.append(Vehicle(self, newVehicle))
                    else:
                        _LOGGER.debug(f'Adding vehicle {vin}, with connectivities: {vehicle.get('connectivities')}')
                        self._vehicles.append(Vehicle(self, newVehicle))
            except:
                raise SeatLoginFailedException("Unable to fetch associated vehicles for account")
        # Update data for all vehicles
        await self.update_all()

        return api_vehicles

 #### API get data functions ####
   # Profile related functions
    #async def getConsentInfo(self):
        """Get consent information for user."""
        """try:
            await self.set_token(self._session_auth_brand)
            atoken = self._session_tokens[self._session_auth_brand]['access_token']
            # Try old pyJWT syntax first
            try:
                subject = jwt.decode(atoken, verify=False).get('sub', None)
            except:
                subject = None
            # Try new pyJWT syntax if old fails
            if subject is None:
                try:
                    exp = jwt.decode(atoken, options={'verify_signature': False}).get('sub', None)
                    subject = exp
                except:
                    raise Exception("Could not extract sub attribute from token")

            data = {'scopeId': 'commonMandatoryFields'}
            response = await self.post(f'https://profileintegrityservice.apps.emea.vwapps.io/iaa/pic/v1/users/{subject}/check-profile', json=data)
            if response.get('mandatoryConsentInfo', False):
                data = {
                    'consentInfo': response
                }
                return data
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch realCarData, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch consent information')
        except Exception as error:
            _LOGGER.debug(f'Could not get consent information, error {error}')
        return False"""

    async def getBasicCarData(self, vin, baseurl):
        """Get car information from customer profile, VIN, nickname, etc."""
        await self.set_token(self._session_auth_brand)
        data={}
        try:
            response = await self.get(eval(f"f'{API_MYCAR}'"))
            if response.get('engines', {}):
                data['mycar']= response
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch vehicle mycar report, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch mycar data')
        except Exception as error:
            _LOGGER.warning(f'Could not fetch mycar report, error: {error}')
        try:
            response = await self.get(eval(f"f'{API_WARNINGLIGHTS}'"))
            if 'statuses' in response:
                data['warninglights'] = response
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch warnlights, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch warnlights')
        except Exception as error:
            _LOGGER.warning(f'Could not fetch warnlights, error: {error}')
        try:
            response = await self.get(eval(f"f'{API_MILEAGE}'"))
            if response.get('mileageKm', {}):
                data['mileage'] = response
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch mileage information, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch mileage information')
        except Exception as error:
            _LOGGER.warning(f'Could not fetch mileage information, error: {error}')
        if data=={}:
            return False
        return data

    #async def getOperationList(self, vin, baseurl):
        """Collect operationlist for VIN, supported/licensed functions."""
        """try:
            #await self.set_token('vwg')
            response = await self.get(f'{baseurl}/api/rolesrights/operationlist/v3/vehicles/{vin}')
            if response.get('operationList', False):
                data = response.get('operationList', {})
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch operation list, HTTP status code: {response.get("status_code")}')
                data = response
            else:
                _LOGGER.info(f'Could not fetch operation list: {response}')
                data = {'error': 'unknown'}
        except Exception as error:
            _LOGGER.warning(f'Could not fetch operation list, error: {error}')
            data = {'error': 'unknown'}
        return data"""

    async def getModelImageURL(self, vin, baseurl):
        """Construct the URL for the model image."""
        await self.set_token(self._session_auth_brand)
        try:
            try:
                response = await self.get(
                    url=eval(f"f'{API_IMAGE}'"),
                )
                if response.get('front',False):
                    images={}
                    for pos in {'front', 'side', 'top', 'rear'}:
                        if pos in response:
                            pic = await self._request(
                                METH_GET,
                                url=response.get(pos,False),
                            )
                            if len(pic)>0:
                                loop = asyncio.get_running_loop()
                                await loop.run_in_executor(None, self.writeImageFile, pos,pic, images)
                    _LOGGER.debug('Read images from web site and wrote them to file.')
                    response['images']=images
                    return response
                else:
                    _LOGGER.debug(f'Could not fetch Model image URL, request returned with status code {response.status_code}')
            except:
                _LOGGER.debug('Could not fetch Model image URL')
        except:
            _LOGGER.debug('Could not fetch Model image URL, message signing failed.')
        return None

    async def getVehicleStatusReport(self, vin, baseurl):
        """Get stored vehicle status report (Connect services)."""
        data={}
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(eval(f"f'{API_STATUS}'"))
            if response.get('doors', False):
                data['status']= response
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch vehicle status report, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch status data')
        except Exception as error:
            _LOGGER.warning(f'Could not fetch status report, error: {error}')
        if data=={}:
            return False
        return data

    async def getMaintenance(self, vin, baseurl):
        """Get stored vehicle status report (Connect services)."""
        data={}
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(eval(f"f'{API_MAINTENANCE}'"))
            if response.get('inspectionDueDays', {}):
                data['maintenance'] = response
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch maintenance information, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch maintenance information')
        except Exception as error:
            _LOGGER.warning(f'Could not fetch maintenance information, error: {error}')
        if data=={}:
            return False
        return data

    async def getTripStatistics(self, vin, baseurl):
        """Get short term and cyclic trip statistics."""
        await self.set_token(self._session_auth_brand)
        try:
            data={'tripstatistics': {}}
            dataType='CYCLIC'
            response = await self.get(eval(f"f'{API_TRIP}'"))
            if response.get('data', []):
                data['tripstatistics']['cyclic']= response.get('data', [])
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch trip statistics, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info(f'Unhandled error while trying to fetch trip statistics')
            dataType='SHORT'
            response = await self.get(eval(f"f'{API_TRIP}'"))
            if response.get('data', []):
                data['tripstatistics']['short']= response.get('data', [])
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch trip statistics, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info(f'Unhandled error while trying to fetch trip statistics')
            if data.get('tripstatistics',{}) != {}:
                return data
        except Exception as error:
            _LOGGER.warning(f'Could not fetch trip statistics, error: {error}')
        return False

    async def getPosition(self, vin, baseurl):
        """Get position data."""
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(eval(f"f'{API_POSITION}'"))
            if response.get('lat', {}):
                data = {
                    'findCarResponse': response,
                    'isMoving': False
                }
                if hasattr(self, '_googleApiKey'):
                    apiKeyForGoogle= self._googleApiKey
                    lat= response.get('lat', 0)
                    lon= response.get('lon', 0)
                    response = await self.get(eval(f"f'{API_POS_TO_ADDRESS}'"))
                    if response.get('routes', []):
                        if response.get('routes', [])[0].get('legs', False):
                            data['findCarResponse']['position_to_address'] = response.get('routes', [])[0].get('legs',[])[0].get('start_address','')
                return data
            elif response.get('status_code', {}):
                if response.get('status_code', 0) == 204:
                    _LOGGER.debug(f'Seems car is moving, HTTP 204 received from position')
                    data = {
                        'isMoving': True,
                        'rate_limit_remaining': 15
                    }
                    return data
                else:
                    _LOGGER.warning(f'Could not fetch position, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch positional data')
        except Exception as error:
            _LOGGER.warning(f'Could not fetch position, error: {error}')
        return False

    async def getDeparturetimer(self, vin, baseurl):
        """Get departure timers."""
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(eval(f"f'{API_DEPARTURE_TIMERS}'"))
            if response.get('timers', {}):
                data={}
                data['departureTimers'] = response
                return data
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch timers, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unknown error while trying to fetch data for departure timers')
        except Exception as error:
            _LOGGER.warning(f'Could not fetch timers, error: {error}')
        return False

    async def getClimater(self, vin, baseurl):
        """Get climatisation data."""
        data={}
        data['climater']={}
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(eval(f"f'{API_CLIMATER_STATUS}'"))
            if response.get('climatisationStatus', {}):
                data['climater']['status']=response
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch climatisation status, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch climatisation status')
        except Exception as error:
            _LOGGER.warning(f'Could not fetch climatisation status, error: {error}')
        try:
            response = await self.get(eval(f"f'{API_CLIMATER}/settings'"))
            if response.get('targetTemperatureInCelsius', {}):
                data['climater']['settings']=response
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch climatisation settings, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch climatisation settings')
        except Exception as error:
            _LOGGER.warning(f'Could not fetch climatisation settings, error: {error}')
        if data['climater']=={}:
            return False
        return data

    async def getCharger(self, vin, baseurl):
        """Get charger data."""
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(eval(f"f'{API_CHARGING}/status'"))
            if response.get('battery', {}):
                chargingStatus = response
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch charging status, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch charging status')
            response = await self.get(eval(f"f'{API_CHARGING}/info'"))
            if response.get('settings', {}):
                chargingInfo = response
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch charging info, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch charging info')
            """response = await self.get(eval(f"f'{API_CHARGING}/modes'"))
            if response.get('battery', {}):
                chargingModes = response
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch charging modes, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch charging modes')"""
            data = {'charging': {
                'status': chargingStatus,
                'info' :  chargingInfo,
                #'modes' :  chargingModes,
            }
            }
            return data
        except Exception as error:
            _LOGGER.warning(f'Could not fetch charger, error: {error}')
        return False

    async def getPreHeater(self, vin, baseurl):
        """Get parking heater data."""
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(eval(f"f'URL_not_yet_known'"))
            if response.get('statusResponse', {}):
                data = {'heating': response.get('statusResponse', {})}
                return data
            elif response.get('status_code', {}):
                _LOGGER.warning(f'Could not fetch pre-heating, HTTP status code: {response.get("status_code")}')
            else:
                _LOGGER.info('Unhandled error while trying to fetch pre-heating data')
        except Exception as error:
            _LOGGER.warning(f'Could not fetch pre-heating, error: {error}')
        return False

 #### API data set functions ####
    #async def get_request_status(self, vin, sectionId, requestId, baseurl):
        """Return status of a request ID for a given section ID."""
        """try:
            error_code = None
            # Requests for VW-Group API
            if sectionId == 'climatisation':
                capability='climatisation'
                url = eval(f"f'{API_REQUESTS}'")
            elif sectionId == 'batterycharge':
                capability='charging'
                url = eval(f"f'{API_REQUESTS}'")
            elif sectionId == 'departuretimer':
                capability='departure-timers'
                url = eval(f"f'{API_REQUESTS}'")
            elif sectionId == 'vsr':
                capability='status'
                url = eval(f"f'{API_REQUESTS}'")
            elif sectionId == 'rhf':
                capability='honkandflash'
                url = eval(f"f'{API_REQUESTS}/status'")
            else:
                capability='unknown'
                url = eval(f"f'{API_REQUESTS}'")

            response = await self.get(url)
            # Pre-heater on older cars
            if response.get('requestStatusResponse', {}).get('status', False):
                result = response.get('requestStatusResponse', {}).get('status', False)
            # Electric charging, climatisation and departure timers
            elif response.get('action', {}).get('actionState', False):
                result = response.get('action', {}).get('actionState', False)
                error_code = response.get('action', {}).get('errorCode', None)
            else:
                result = 'Unknown'
            # Translate status messages to meaningful info
            if result in ['request_in_progress', 'queued', 'fetched', 'InProgress', 'Waiting']:
                status = 'In progress'
            elif result in ['request_fail', 'failed']:
                status = 'Failed'
                if error_code is not None:
                    # Identified error code for charging, 11 = not connected
                    if sectionId == 'charging' and error_code == 11:
                        _LOGGER.info(f'Request failed, charger is not connected')
                    else:
                        _LOGGER.info(f'Request failed with error code: {error_code}')
            elif result in ['unfetched', 'delayed', 'PollingTimeout']:
                status = 'No response'
            elif result in [ "FailPlugDisconnected", "FailTimerChargingActive" ]:
                status = "Unavailable"
            elif result in ['request_successful', 'succeeded', "Successful"]:
                status = 'Success'
            else:
                status = result
            return status
        except Exception as error:
            _LOGGER.warning(f'Failure during get request status: {error}')
            raise SeatException(f'Failure during get request status: {error}')"""

    async def get_sec_token(self, spin, baseurl):
        """Get a security token, required for certain set functions."""
        data = {'spin': spin}
        url = eval(f"f'{API_SECTOKEN}'")
        response = await self.post(url, json=data, allow_redirects=True)
        if response.get('securityToken', False):
            return response['securityToken']
        else:
            raise SeatException('Did not receive a valid security token. Maybewrong SPIN?' )

    async def _setViaAPI(self, endpoint, **data):
        """Data call to API to set a value or to start an action."""
        await self.set_token(self._session_auth_brand)
        try:
            url = endpoint 
            response = await self._data_call(url, **data)
            if not response:
                raise SeatException(f'Invalid or no response for endpoint {endpoint}')
            elif response == 429:
                raise SeatThrottledException('Action rate limit reached. Start the car to reset the action limit')
            else:
                data = {'id': '', 'state' : ''}
                if 'requestId' in response:
                    data['state'] = 'Request accepted'
                for key in response:
                    if isinstance(response.get(key), dict):
                        for k in response.get(key):
                            if 'id' in k.lower():
                                data['id'] = str(response.get(key).get(k))
                            if 'state' in k.lower():
                                data['state'] = response.get(key).get(k)
                    else:
                        if 'Id' in key:
                            data['id'] = str(response.get(key))
                        if 'State' in key:
                            data['state'] = response.get(key)
                if response.get('rate_limit_remaining', False):
                    data['rate_limit_remaining'] = response.get('rate_limit_remaining', None)
                return data
        except:
            raise
        return False

    async def setCharger(self, vin, baseurl, mode, data):
        """Start/Stop charger."""
        if mode in {'start', 'stop'}:
            capability='charging'
            return await self._setViaAPI(eval(f"f'{API_REQUESTS}/{mode}'"))
        else:
            _LOGGER.error(f'Not yet implemented. Mode: {mode}. Command ignored')
            raise

    async def setClimater(self, vin, baseurl, mode, data, spin):
        """Execute climatisation actions."""
        try:
            # Only get security token if auxiliary heater is to be started
            if data.get('action', {}).get('settings', {}).get('heaterSource', None) == 'auxiliary':
                _LOGGER.error(f'This action is not yet implemented: {data.get('action', {}).get('settings', {}).get('heaterSource', None)}. Command ignored')
                #self._session_headers['X-securityToken'] = await self.get_sec_token(vin=vin, spin=spin, action='rclima', baseurl=baseurl)
                pass
            if mode == "stop": # Stop climatisation
                capability='climatisation'
                return await self._setViaAPI(eval(f"f'{API_REQUESTS}/stop'"))
            elif mode == "settings": # Set target temperature
                capability='climatisation'
                return await self._setViaAPI(eval(f"f'{API_CLIMATER}/settings'"), json=data)
            elif mode == "windowHeater stop": # Stop window heater
                capability='windowheating'
                return await self._setViaAPI(eval(f"f'{API_REQUESTS}/stop'"))
            elif mode == "windowHeater start": # Stop window heater
                capability='windowheating'
                return await self._setViaAPI(eval(f"f'{API_REQUESTS}/start'"))
            elif mode == "start": # Start climatisation
                return await self._setViaAPI(eval(f"f'{API_CLIMATER}/start'"), json = data)
            else: # Unknown modes
                _LOGGER.error(f'Unbekannter setClimater mode: {mode}. Command ignored')
                return False
        except:
            raise
        return False

    async def setDeparturetimer(self, vin, baseurl, data, spin):
        """Set departure timers."""
        try:
            url= eval(f"f'{API_DEPARTURE_TIMERS}'")
            if data:
                if data.get('minSocPercentage',False):
                    url=url+'/settings'
            return await self._setViaAPI(url, json = data)
        except:
            raise
        return False

    async def sendDestination(self, vin, baseurl, data, spin):
        """Send destination to vehicle."""

        await self.set_token(self._session_auth_brand)
        try:
            url= eval(f"f'{API_DESTINATION}'")
            response = await self._session.request(
                METH_PUT,
                url,
                headers=self._session_headers,
                timeout=ClientTimeout(total=TIMEOUT.seconds),
                cookies=self._session_cookies,
                raise_for_status=False,
                json=data
                )
            if response.status==202: #[202 Accepted]
                _LOGGER.debug(f'Destination {data[0]} successfully sent to API.')
                return response
            else:
                _LOGGER.debug(f'API did not successfully receive destination.')
                raise SeatException(f'Invalid or no response for endpoint {url}')
                return response
        except aiohttp.client_exceptions.ClientResponseError as error:
            _LOGGER.debug(f'Request failed. Data: {data}, HTTP request headers: {self._session_headers}')
            if error.status == 401:
                _LOGGER.error('Unauthorized')
            elif error.status == 400:
                _LOGGER.error(f'Bad request')
            elif error.status == 429:
                _LOGGER.warning('Too many requests. Further requests can only be made after the end of next trip in order to protect your vehicles battery.')
                return 429
            elif error.status == 500:
                _LOGGER.error('Internal server error, server might be temporarily unavailable')
            elif error.status == 502:
                _LOGGER.error('Bad gateway, this function may not be implemented for this vehicle')
            else:
                _LOGGER.error(f'Unhandled HTTP exception: {error}')
            #return False
        except Exception as error:
            _LOGGER.error(f'Error: {error}')
            raise
        return False

    async def setHonkAndFlash(self, vin, baseurl, data):
        """Execute honk and flash actions."""
        return await self._setViaAPI(eval(f"f'{API_HONK_AND_FLASH}'"), json = data)

    async def setLock(self, vin, baseurl, action, data, spin):
        """Remote lock and unlock actions."""
        try:
            # Fetch security token 
            self._session_headers['SecToken']= await self.get_sec_token(spin=spin, baseurl=baseurl)

            response = await self._setViaAPI(eval(f"f'{API_ACCESS}'"))

            # Clean up headers
            self._session_headers.pop('SecToken')

            return response

        except:
            self._session_headers.pop('SecToken')
            raise
        return False

    async def setPreHeater(self, vin, baseurl, data, spin):
        """Petrol/diesel parking heater actions."""
        try:
            # Fetch security token 
            self._session_headers['SecToken']= await self.get_sec_token(spin=spin, baseurl=baseurl)

            response = await self._setViaAPI(eval(f"f'url_not_yet_known'"), json = data)

            # Clean up headers
            self._session_headers.pop('SecToken')

            return response

        except:
            self._session_headers.pop('SecToken')
            raise
        return False

    async def setRefresh(self, vin, baseurl):
        """"Force vehicle data update."""
        return await self._setViaAPI(eval(f"f'{API_REFRESH}'"))

 #### Token handling ####
    async def validate_token(self, token):
        """Function to validate a single token."""
        try:
            now = datetime.now()
            # Try old pyJWT syntax first
            try:
                exp = jwt.decode(token, verify=False).get('exp', None)
            except:
                exp = None
            # Try new pyJWT syntax if old fails
            if exp is None:
                try:
                    exp = jwt.decode(token, options={'verify_signature': False}).get('exp', None)
                except:
                    raise Exception("Could not extract exp attribute")

            expires = datetime.fromtimestamp(int(exp))

            # Lazy check but it's very inprobable that the token expires the very second we want to use it
            if expires > now:
                return expires
            else:
                _LOGGER.debug(f'Token expired at {expires.strftime("%Y-%m-%d %H:%M:%S")})')
                return False
        except Exception as e:
            _LOGGER.info(f'Token validation failed, {e}')
        return False

    async def verify_token(self, token):
        """Function to verify a single token."""
        try:
            req = None
            # Try old pyJWT syntax first
            try:
                aud = jwt.decode(token, verify=False).get('aud', None)
            except:
                aud = None
            # Try new pyJWT syntax if old fails
            if aud is None:
                try:
                    aud = jwt.decode(token, options={'verify_signature': False}).get('aud', None)
                except:
                    raise Exception("Could not extract exp attribute")

            if not isinstance(aud, str):
                aud = next(iter(aud))
            _LOGGER.debug(f"Verifying token for {aud}")
            # If audience indicates a client from https://identity.vwgroup.io
            for client in CLIENT_LIST:
                if self._session_fulldebug:
                    _LOGGER.debug(f"Matching {aud} against {CLIENT_LIST[client].get('CLIENT_ID', '')}")
                if aud == CLIENT_LIST[client].get('CLIENT_ID', ''):
                    req = await self._session.get(url = AUTH_TOKENKEYS)
                    break

            # Fetch key list
            keys = await req.json()
            pubkeys = {}
            # Convert all RSA keys and store in list
            for jwk in keys['keys']:
                kid = jwk['kid']
                if jwk['kty'] == 'RSA':
                    pubkeys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(to_json(jwk))
            # Get key ID from token and get match from key list
            token_kid = jwt.get_unverified_header(token)['kid']
            if self._session_fulldebug:
                try:
                    _LOGGER.debug(f'Token Key ID is {token_kid}, match from public keys: {keys["keys"][token_kid]}')
                except:
                    pass
            pubkey = pubkeys[token_kid]

            # Verify token with public key
            if jwt.decode(token, key=pubkey, algorithms=['RS256'], audience=aud):
                return True
        except ExpiredSignatureError:
            return False
        except Exception as error:
            _LOGGER.debug(f'Failed to verify {aud} token, error: {error}')
            return error

    async def refresh_token(self, client):
        """Function to refresh tokens for a client."""
        try:
            # Refresh API tokens
            _LOGGER.debug(f'Refreshing tokens for client "{client}"')
            if client != 'vwg':
                body = {
                    'grant_type': 'refresh_token',
                    'client_id': CLIENT_LIST[client].get('CLIENT_ID'),
                    'client_secret': CLIENT_LIST[client].get('CLIENT_SECRET'),
                    'refresh_token': self._session_tokens[client]['refresh_token']
                }
                url = AUTH_REFRESH
                self._session_token_headers[client]['User-ID']=self._user_id
                self._session_headers['User-ID']=self._user_id
            else:
                _LOGGER.error(f'refresh_token() does not support client \'{client}\' ')
                raise
            #    body = {
            #        'grant_type': 'refresh_token',
            #        'scope': 'sc2:fal',
            #        'token': self._session_tokens[client]['refresh_token']
            #    }
            #    url = 'https://mbboauth-1d.prd.ece.vwg-connect.com/mbbcoauth/mobile/oauth2/v1/token'

            try:
                response = await self._session.post(
                    url=url,
                    headers=self._session_token_headers.get(client),
                    data = body,
                )
            except:
                raise

            if response.status == 200:
                tokens = await response.json()
                # Verify access_token
                if 'access_token' in tokens:
                    if not await self.verify_token(tokens['access_token']):
                        _LOGGER.warning('Tokens could not be verified!')
                for token in tokens:
                    self._session_tokens[client][token] = tokens[token]
                return True
            elif response.status == 400:
                error = await response.json()
                if error.get('error', {}) == 'invalid_grant':
                    _LOGGER.debug(f'VW-Group API token refresh failed: {error.get("error_description", {})}')
                    #if client == 'vwg':
                    #    return await self._getAPITokens()
            else:
                resp = await response.json()
                _LOGGER.warning(f'Something went wrong when refreshing tokens for "{client}".')
                _LOGGER.debug(f'Headers: {TOKEN_HEADERS.get(client)}')
                _LOGGER.debug(f'Request Body: {body}')
                _LOGGER.warning(f'Something went wrong when refreshing VW-Group API tokens.')
        except Exception as error:
            _LOGGER.warning(f'Could not refresh tokens: {error}')
        return False

    async def set_token(self, client):
        """Switch between tokens."""
        # Lock to prevent multiple instances updating tokens simultaneously
        async with self._lock:
            # If no tokens are available for client, try to authorize
            tokens = self._session_tokens.get(client, None)
            if tokens is None:
                _LOGGER.debug(f'Client "{client}" token is missing, call to authorize the client.')
                try:
                    # Try to authorize client and get tokens
                    if client != 'vwg':
                        result = await self._authorize(client)
                    else:
                        _LOGGER.error('getAPITokens() commented out.')
                        result = False
                        #result = await self._getAPITokens()

                    # If authorization wasn't successful
                    if result is not True:
                        raise SeatAuthenticationException(f'Failed to authorize client {client}')
                except:
                    raise
            try:
                # Validate access token for client, refresh if validation fails
                valid = await self.validate_token(self._session_tokens.get(client, {}).get('access_token', ''))
                if not valid:
                    _LOGGER.debug(f'Tokens for "{client}" are invalid')
                    # Try to refresh tokens for client
                    if await self.refresh_token(client) is not True:
                        raise SeatTokenExpiredException(f'Tokens for client {client} are invalid')
                    else:
                        _LOGGER.debug(f'Tokens refreshed successfully for client "{client}"')
                        pass
                else:
                    try:
                        dt = datetime.fromtimestamp(valid)
                        _LOGGER.debug(f'Access token for "{client}" is valid until {dt.strftime("%Y-%m-%d %H:%M:%S")}')
                    except:
                        pass
                # Assign token to authorization header
                self._session_headers['Authorization'] = 'Bearer ' + self._session_tokens[client]['access_token']
            except:
                raise SeatException(f'Failed to set token for "{client}"')
            return True

 #### Class helpers ####
    @property
    def vehicles(self):
        """Return list of Vehicle objects."""
        return self._vehicles

    def vehicle(self, vin):
        """Return vehicle object for given vin."""
        return next(
            (
                vehicle
                for vehicle in self.vehicles
                if vehicle.unique_id.lower() == vin.lower()
            ), None
        )

    def hash_spin(self, challenge, spin):
        """Convert SPIN and challenge to hash."""
        spinArray = bytearray.fromhex(spin);
        byteChallenge = bytearray.fromhex(challenge);
        spinArray.extend(byteChallenge)
        return hashlib.sha512(spinArray).hexdigest()

async def main():
    """Main method."""
    if '-v' in argv:
        logging.basicConfig(level=logging.INFO)
    elif '-vv' in argv:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    async with ClientSession(headers={'Connection': 'keep-alive'}) as session:
        connection = Connection(session, **read_config())
        if await connection.doLogin():
            if await connection.get_vehicles():
                for vehicle in connection.vehicles:
                    print(f'Vehicle id: {vehicle}')
                    print('Supported sensors:')
                    for instrument in vehicle.dashboard().instruments:
                        print(f' - {instrument.name} (domain:{instrument.component}) - {instrument.str_state}')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
