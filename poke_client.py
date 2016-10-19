from auth import AuthPTC, AuthGoogle
from location import Location
from utils import get_args
from ConsistentHash import Client


args = get_args()
location = Location(args.location)
if args.auth_service == 'ptc':
    auth = AuthPTC(location)
elif args.auth_service == 'google':
    auth = AuthGoogle(location)
else:
    raise Exception("Invalid service '{}'".format(args.auth_service))

auth.login(auth.username, auth.password)

n = Client(args.host, args.port)
resp = n.send_request({'auth': auth.get_auth_data()})
if not resp['status']:
    raise Exception('Unable to set auth data: {}'.format(resp['msg']))

for lat, lon in location.steps(args.steplimit):
    bearing = location.get_bearing(lat, lon)
    data = n.send_request({'key': bearing, 'lat': lat, 'lon': lon})
    print(data)
