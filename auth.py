import json
import pokemon_pb2
import time
from gpsoauth import perform_master_login, perform_oauth
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from collections import namedtuple

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

API_URL = 'https://pgorelease.nianticlabs.com/plfe/rpc'
LOGIN_URL = 'https://sso.pokemon.com/sso/login?service=https://sso.pokemon.com/sso/oauth2.0/callbackAuthorize'
LOGIN_OAUTH = 'https://sso.pokemon.com/sso/oauth2.0/accessToken'
APP = 'com.nianticlabs.pokemongo'

with open('credentials.json') as file:
	credentials = json.load(file)

PTC_CLIENT_SECRET = credentials.get('ptc_client_secret', None)
ANDROID_ID = credentials.get('android_id', None)
SERVICE = credentials.get('service', None)
CLIENT_SIG = credentials.get('client_sig', None)
GOOGLEMAPS_KEY = credentials.get('gmaps_key', None)

SESSION = requests.session()
SESSION.headers.update({'User-Agent': 'Niantic App'})
SESSION.verify = False

class Auth(object):
    def __init__(self, location):
        self.api_endpoint = None
        self.access_token = None
        self.profile_response = None
        self.location = location

    def get_auth_data(self):
        return [self.service, self.api_endpoint, self.access_token, self.profile_response]

    def retrying_api_req(self, api_endpoint, access_token, *args, **kwargs):
        while True:
            try:
                response = api_req(api_endpoint, access_token, *args,
                                   **kwargs)
                if response:
                    return response
                print('retrying_api_req: api_req returned None, retrying')
            except (InvalidURL, ConnectionError, DecodeError), e:
                print('retrying_api_req: request error ({}), retrying'.format(
                    str(e)))
            time.sleep(1)


    def api_req(self, api_endpoint, access_token, *args, **kwargs):
        p_req = pokemon_pb2.RequestEnvelop()
        p_req.rpc_id = 1469378659230941192

        p_req.unknown1 = 2

        (p_req.latitude, p_req.longitude, p_req.altitude) = \
            self.location.get_location_coords()

        p_req.unknown12 = 989

        if 'useauth' not in kwargs or not kwargs['useauth']:
            p_req.auth.provider = self.service
            p_req.auth.token.contents = access_token
            p_req.auth.token.unknown13 = 14
        else:
            p_req.unknown11.unknown71 = kwargs['useauth'].unknown71
            p_req.unknown11.unknown72 = kwargs['useauth'].unknown72
            p_req.unknown11.unknown73 = kwargs['useauth'].unknown73

        for arg in args:
            p_req.MergeFrom(arg)

        protobuf = p_req.SerializeToString()

        r = SESSION.post(api_endpoint, data=protobuf, verify=False)

        p_ret = pokemon_pb2.ResponseEnvelop()
        p_ret.ParseFromString(r.content)

        time.sleep(0.51)
        return p_ret

    def _get_profile(self, access_token, api, useauth):
        req = pokemon_pb2.RequestEnvelop()
        req1 = req.requests.add()
        req1.type = 2

        req2 = req.requests.add()
        req2.type = 126
        if len(reqq) >= 2:
            req2.MergeFrom(reqq[1])

        req3 = req.requests.add()
        req3.type = 4
        if len(reqq) >= 3:
            req3.MergeFrom(reqq[2])

        req4 = req.requests.add()
        req4.type = 129
        if len(reqq) >= 4:
            req4.MergeFrom(reqq[3])

        req5 = req.requests.add()
        req5.type = 5
        if len(reqq) >= 5:
            req5.MergeFrom(reqq[4])
        return self.retrying_api_req(api, access_token, req, useauth=useauth)

    def get_profile(self, access_token, api, useauth):
        profile_response = None
        while not profile_response:
            profile_response = self._get_profile(access_token, api, useauth)
            if not hasattr(profile_response, 'payload'):
                print(
                    'retrying_get_profile: get_profile returned no payload, retrying')
                profile_response = None
                continue
            if not profile_response.payload:
                print(
                    'retrying_get_profile: get_profile returned no-len payload, retrying')
                profile_response = None

        return profile_response

    def get_api_endpoint(service, access_token, api=API_URL):
        profile_response = None
        while not profile_response:
            profile_response = self.get_profile(access_token, api, None)
            if not hasattr(profile_response, 'api_url'):
                print(
                    'retrying_get_profile: get_profile returned no api_url, retrying')
                profile_response = None
                continue
            if not len(profile_response.api_url):
                print(
                    'get_api_endpoint: retrying_get_profile returned no-len api_url, retrying')
                profile_response = None

        return 'https://%s/rpc' % profile_response.api_url

    def get_token(self, username, password):
        raise NotImplementedError

    def login(self, user, password):
        access_token = self.get_token(user, password)
        if access_token is None:
            raise Exception('[-] Wrong username/password')

        print('[+] RPC Session Token: {} ...'.format(access_token[:25]))

        api_endpoint = self.get_api_endpoint(args.auth_service, access_token)
        if api_endpoint is None:
            raise Exception('[-] RPC server offline')

        print('[+] Received API endpoint: {}'.format(api_endpoint))

        profile_response = self.get_profile(access_token, api_endpoint)
        if profile_response is None or not profile_response.payload:
            raise Exception('Could not get profile')

        print('[+] Login successful')

        payload = profile_response.payload[0]
        profile = pokemon_pb2.ResponseEnvelop.ProfilePayload()
        profile.ParseFromString(payload)
        print('[+] Username: {}'.format(profile.profile.username))

        creation_time = \
            datetime.fromtimestamp(int(profile.profile.creation_time)
                                   / 1000)
        print '[+] You started playing Pokemon Go on: {}'.format(
            creation_time.strftime('%Y-%m-%d %H:%M:%S'))

        for curr in profile.profile.currency:
            print '[+] {}: {}'.format(curr.type, curr.amount)

        return api_endpoint, access_token, profile_response

class AuthPTC(Auth):
    def __init__(self):
        self.service = 'ptc'
        super(AuthGoogle, self).__init__()

    def get_token(self, username, password):
        print('[!] PTC login for: {}'.format(username))
        head = {'User-Agent': 'Niantic App'}
        r = SESSION.get(LOGIN_URL, headers=head)
        if r is None:
            raise Exception("Servers don't like you")

        try:
            jdata = json.loads(r.content)
        except ValueError, e:
            raise Exception('login_ptc: could not decode JSON from {}'.format(r.content))

        # Maximum password length is 15 (sign in page enforces this limit, API does not)
        if len(password) > 15:
            print('[!] Trimming password to 15 characters')
            password = password[:15]

        data = {
            'lt': jdata['lt'],
            'execution': jdata['execution'],
            '_eventId': 'submit',
            'username': username,
            'password': password,
        }
        r1 = SESSION.post(LOGIN_URL, data=data, headers=head)

        ticket = None
        try:
            ticket = re.sub('.*ticket=', '', r1.history[0].headers['Location'])
        except Exception, e:
            raise(r1.json()['errors'][0])

        data1 = {
            'client_id': 'mobile-app_pokemon-go',
            'redirect_uri': 'https://www.nianticlabs.com/pokemongo/error',
            'client_secret': PTC_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'code': ticket,
        }
        r2 = SESSION.post(LOGIN_OAUTH, data=data1)
        access_token = re.sub('&expires.*', '', r2.content)
        access_token = re.sub('.*access_token=', '', access_token)

        return access_token

class AuthGoogle(Auth):
    def __init__(self):
        self.service = 'google'
        super(AuthGoogle, self).__init__()

    def get_token(self, username, password):
        print('[!] Google login for: {}'.format(username))
        r1 = perform_master_login(username, password, ANDROID_ID)
        r2 = perform_oauth(username,
                           r1.get('Token', ''),
                           ANDROID_ID,
                           SERVICE,
                           APP,
                           CLIENT_SIG, )
        return r2.get('Auth')
