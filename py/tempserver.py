#!/home/matt/templog/venv/bin/python

import sys
import os
import logging

import gevent
import gevent.monkey
import lockfile
import daemon

import utils
from utils import L,D,EX,W
import fridge
import config
import sensor_ds18b20
import params
import uploader


class Tempserver(object):
    def __init__(self):
        self.readings = []
        self.current = (None, None)
        self.fridge = None

        # don't patch os, fork() is used by daemonize
        gevent.monkey.patch_all(os=False, thread=False)

    def __enter__(self):
        self.params = params.Params()
        self.fridge = fridge.Fridge(self)
        self.uploader = uploader.Uploader(self)
        self.params.load()
        self.set_sensors(sensor_ds18b20.DS18B20s(self))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        L("Exiting, cleanup handler");
        self.fridge.off()

    def run(self):

        if self.fridge is None:
            raise Exception("Tempserver.run() must be within 'with Tempserver() as server'")

        # XXX do these go here or in __enter_() ?
        self.start_time = self.now()
        self.fridge.start()
        self.sensors.start()
        self.uploader.start()

        # won't return.
        while True:
            try:
                gevent.sleep(60)
            except KeyboardInterrupt:
                break

    def now(self):
        return utils.monotonic_time()

    def set_sensors(self, sensors):
        if hasattr(self, 'sensors'):
            self.sensors.kill()
        self.sensors = sensors
        self.wort_name = sensors.wort_name()
        self.fridge_name = sensors.fridge_name()

    def take_readings(self):
        ret = self.readings
        self.readings = []
        return ret

    def pushfront(self, readings):
        """ used if a caller of take_readings() fails """
        self.readings = readings + self.readings

    # a reading is a map of {sensorname: value}. temperatures
    # are float degrees
    def add_reading(self, reading):
        """ adds a reading at the current time """
        D("add_reading(%s)" % str(reading))
        self.readings.append( (reading, self.now()))
        self.current = (reading.get(self.wort_name, None),
                    reading.get(self.fridge_name, None))
        if len(self.readings) > config.MAX_READINGS:
            self.readings = self.readings[-config.MAX_READINGS:]

    def current_temps(self):
        """ returns (wort_temp, fridge_temp) tuple """
        return self.current

def setup_logging():
    logging.basicConfig(format='%(asctime)s %(message)s', 
            datefmt='%m/%d/%Y %I:%M:%S %p',
            level=logging.DEBUG)

def start():
    with Tempserver() as server:
        server.run()

def main():
    setup_logging()

    pidpath = os.path.join(os.path.dirname(__file__), 'tempserver-lock')
    pidf = lockfile.FileLock(pidpath, threaded=False)
    pidf.acquire(0)

    if '--daemon' in sys.argv:
        logpath = os.path.join(os.path.dirname(__file__), 'tempserver.log')
        logf = open(logpath, 'a+')
        with daemon.DaemonContext(pidfile=pidf, stdout=logf, stderr = logf):
            start()
    else:
        with pidf:
            start()

if __name__ == '__main__':
    main()
