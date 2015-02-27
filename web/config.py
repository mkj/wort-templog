# for server
BTADDR = "00:12:03:27:70:88"
SLEEP_TIME = 60
SERIAL_HOST='home.example.com'
SERIAL_PORT=1999


DATA_PATH = '/home/matt/templog/web/data'

# local config items
HMAC_KEY = 'a hmac key' 
ALLOWED_USERS = [] # list of sha1 hashes of client ssl keys
SSH_HOST = 'remotehost'
SSH_KEYFILE = '/home/matt/.ssh/somekey'
SSH_PROG = 'ssh'

UPDATE_URL = 'http://evil.ucc.asn.au/~matt/templog/update'

GRAPH_WIDTH = 1200
GRAPH_HEIGHT = 600
ZOOM = 1

LINE_WIDTH = 2

SENSOR_NAMES = {'sensor_28 CE B2 1A 03 00 00 99': "Old Fridge",
    'sensor_28 CC C1 1A 03 00 00 D4': "Old Ambient",
    'sensor_28 49 BC 1A 03 00 00 54': "Old Wort",
    'sensor_voltage': 'Voltage',
    'sensor_fridge_setpoint': 'Setpoint',
    'sensor_fridge_on': 'Cool',
    'sensor_28-0000042cf4dd': "Wort",
    'sensor_28-0000042cccc4': "Fridge",
    'sensor_28-0000042c6dbb': "Ambient",
    'sensor_internal': "Processor",
    }

# print legend for these ones
LEGEND_NAMES = set(("Wort", "Fridge", "Ambient", "Setpoint"))

SENSOR_COLOURS = {'Wort': 'e49222', 
                'Ambient': '028b3d',
                'Voltage': '7db5d3aa',
                'Fridge': '93c8ff',
                'Setpoint': '39c662',
                'Cool': 'd7cedd',
                'Processor': 'bf7a69',
                }


GRAPH_FONT = "Prociono"
#GRAPH_FONT = "URW Gothic L"

# determine by zooming in an image viewer
GRAPH_LEFT_MARGIN = 63

# 1 hour
CSRF_TIMEOUT = 3600

try:
    from localconfig import *
except ImportError:
    pass
