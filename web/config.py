
DATA_PATH = '/home/matt/templog/web/data'

HMAC_KEY = 'a hmac key'

UPDATE_URL = 'https://evil.ucc.asn.au/~matt/templog/update'

GRAPH_WIDTH = 1200
GRAPH_HEIGHT = 600
ZOOM = 1

LINE_WIDTH = 2

SENSOR_NAMES = {'sensor_28 CE B2 1A 03 00 00 99': "Wort",
    'sensor_28 CC C1 1A 03 00 00 D4': "Ambient",
    'sensor_28 49 BC 1A 03 00 00 54': "Other",
    'sensor_voltage': 'Voltage',
    }

SENSOR_COLOURS = {'Wort': 'e49222', 
                'Ambient': '028b3d',
                'Voltage': '7db5d3aa',
                'Other': '78000c',
                }


GRAPH_FONT = "Prociono"
#GRAPH_FONT = "URW Gothic L"

# determine by zooming in an image viewer
GRAPH_LEFT_MARGIN = 63
