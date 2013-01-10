
FRIDGE_SLEEP = 60
SENSOR_SLEEP = 15
UPLOAD_SLEEP = 80

FRIDGE_DELAY = 600 # 10 mins
FRIDGE_WORT_INVALID_TIME = 300 # 5 mins

# 12 hours
MAX_READINGS = 12*60*60 / SENSOR_SLEEP

PARAMS_FILE = './tempserver.conf'

SENSOR_BASE_DIR = '/sys/devices/w1_bus_master1'
FRIDGE_GPIO = '/sys/devices/virtual/gpio/gpio17'
WORT_NAME = '28-0000042cf4dd'
FRIDGE_NAME = '28-0000042cccc4'
AMBIENT_NAME = '28-0000042c6dbb'
INTERNAL_TEMPERATURE = '/sys/class/thermal/thermal_zone0/temp'

HMAC_KEY = "a key"
UPDATE_URL = 'https://matt.ucc.asn.au/test/templog/update'

try:
    from localconfig import *
except ImportError:
    pass
