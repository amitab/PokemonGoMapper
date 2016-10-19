import pokemon_pb2
from google.protobuf.internal import encoder
from s2sphere import *
import time
from utils import f2i
from ConsistentHash import Server

def encode(cellid):
    output = []
    encoder._VarintEncoder()(output.append, cellid)
    return ''.join(output)

def getNeighbors(lat, lon):
    origin = CellId.from_lat_lng(LatLng.from_degrees(lat, lon)).parent(15)
    walk = [origin.id()]

    # 10 before and 10 after

    next = origin.next()
    prev = origin.prev()
    for i in range(10):
        walk.append(prev.id())
        walk.append(next.id())
        next = next.next()
        prev = prev.prev()
    return walk

def get_heartbeat(service, api_endpoint, access_token, response, lat, lon):
    m4 = pokemon_pb2.RequestEnvelop.Requests()
    m = pokemon_pb2.RequestEnvelop.MessageSingleInt()
    m.f1 = int(time.time() * 1000)
    m4.message = m.SerializeToString()
    m5 = pokemon_pb2.RequestEnvelop.Requests()
    m = pokemon_pb2.RequestEnvelop.MessageSingleString()
    m.bytes = '05daf51635c82611d1aac95c0b051d3ec088a930'
    m5.message = m.SerializeToString()
    walk = sorted(getNeighbors(lat, lon))
    m1 = pokemon_pb2.RequestEnvelop.Requests()
    m1.type = 106
    m = pokemon_pb2.RequestEnvelop.MessageQuad()
    m.f1 = ''.join(map(encode, walk))
    m.f2 = \
        "\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000"
    m.lat = f2i(lat)
    m.long = f2i(lon)
    m1.message = m.SerializeToString()
    response = get_profile(service,
                           access_token,
                           api_endpoint,
                           response.unknown7,
                           m1,
                           pokemon_pb2.RequestEnvelop.Requests(),
                           m4,
                           pokemon_pb2.RequestEnvelop.Requests(),
                           m5, )

    try:
        payload = response.payload[0]
    except (AttributeError, IndexError):
        return

    heartbeat = pokemon_pb2.ResponseEnvelop.HeartbeatPayload()
    heartbeat.ParseFromString(payload)
    return heartbeat

class PokemonLocation(object):
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
        self.pokemons = {}
        self.gyms = {}
        self.pokestops = {}

    def clear_stale(self):
        current_time = time.time()

        for pokemon_key in self.pokemons.keys():
            pokemon = self.pokemons[pokemon_key]
            if current_time > pokemon['disappear_time']:
                print("[+] removing stale pokemon %s at %f, %f from list" % (
                    pokemon['name'].encode('utf-8'), pokemon['lat'], pokemon['lng']))
                del self.pokemons[pokemon_key]

class PokemonLocator(object):
    def __init__(self):
        self.coords = {}

    def clear_stale_pokemons():
        for coord in self.coords:
            self.coords[coord].clear_stale()

    def pokemons_at(self, lat, lon, auth):
        if hash((lat, lon,)) in self.coords:
            self.coords[hash((lat, lon,))] = PokemonLocation(lat, lon)

        loc = self.coords[hash((lat, lon,))]
        origin = LatLng.from_degrees(lat, lon)
        step_lat = lat
        step_long = lon
        parent = CellId.from_lat_lng(LatLng.from_degrees(lat, lon)).parent(15)
        h = get_heartbeat(auth.service, auth.api_endpoint, auth.access_token, auth.profile_response)
        hs = [h]
        seen = {}

        for child in parent.children():
            latlng = LatLng.from_point(Cell(child).get_center())
            hs.append(
                get_heartbeat(auth.service, auth.api_endpoint, auth.access_token, auth.profile_response))

        visible = []

        for hh in hs:
            try:
                for cell in hh.cells:
                    for wild in cell.WildPokemon:
                        hash = wild.SpawnPointId;
                        if hash not in seen.keys() or (seen[hash].TimeTillHiddenMs <= wild.TimeTillHiddenMs):
                            visible.append(wild)    
                        seen[hash] = wild.TimeTillHiddenMs
                    if cell.Fort:
                        for Fort in cell.Fort:
                            if Fort.Enabled == True:
                                if Fort.GymPoints:
                                    loc.gyms[Fort.FortId] = [Fort.Team, Fort.Latitude,
                                                         Fort.Longitude, Fort.GymPoints]

                                elif Fort.FortType:
                                    expire_time = 0
                                    if Fort.LureInfo.LureExpiresTimestampMs:
                                        expire_time = datetime\
                                            .fromtimestamp(Fort.LureInfo.LureExpiresTimestampMs / 1000.0)\
                                            .strftime("%H:%M:%S")
                                    if expire_time != 0:
                                        loc.pokestops[Fort.FortId] = [Fort.Latitude,
                                                                  Fort.Longitude, expire_time]
            except AttributeError:
                break

        for poke in visible:
            disappear_timestamp = time.time() + poke.TimeTillHiddenMs / 1000

            loc.pokemons[poke.SpawnPointId] = {
                "lat": poke.Latitude,
                "lng": poke.Longitude,
                "disappear_time": disappear_timestamp,
                "id": poke.pokemon.PokemonId
            }

        return loc

def PokemonServer(Server):
    AuthData = namedtuple('AuthData', ['service', 'api_endpoint', 'access_token', 'response'])

    def __init__(self, host, port, max_con=100, refuse=200):
        self.auth = None
        self.locator = PokemonLocator()
        super(PokemonServer, self).__init__(host, port, max_con, refuse)

    def handle_command(self, data):
        if self.auth is None and 'auth' not in data:
            return {'status': False, 'msg': 'Need auth before continuing'}
        if 'auth' in data:
            try:
                self.auth = PokemonServer.AuthData(*data['auth'])
                return {'status': True}
            except Exception as err:
                return {'status': False, 'msg': '{}'.format(err)}
        elif 'lat' in data and 'lon' in data:
            return self.locator.pokemons_at(data['lat'], data['lon'], self.auth)
        return {'status': False, 'msg': 'Unrecognized Command'}
