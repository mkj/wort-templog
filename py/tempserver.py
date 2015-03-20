#!/home/matt/templog/venv/bin/python

import sys
import os
import logging
import time
import signal
import asyncio

import lockfile.pidlockfile
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
        self._wakeup = asyncio.Event()

    def __enter__(self):
        self.params = params.Params()
        self.fridge = fridge.Fridge(self)
        self.uploader = uploader.Uploader(self)
        self.params.load()
        self.set_sensors(sensor_ds18b20.DS18B20s(self))
        asyncio.get_event_loop().add_signal_handler(signal.SIGHUP, self._reload_signal)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        L("Exiting, cleanup handler");
        self.fridge.off()

    def run(self):

        if self.fridge is None:
            raise Exception("Tempserver.run() must be within 'with Tempserver() as server'")

        # XXX do these go here or in __enter_() ?
        self.start_time = self.now()
        tasks = (
            self.fridge.run(),
            self.sensors.run(),
            self.uploader.run(),
        )
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(asyncio.wait(tasks))
            # not reached
        except KeyboardInterrupt:
            pass

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

    def sleep(self, timeout):
        """ sleeps for timeout seconds, though wakes if the server's config is updated """
        asyncio.wait_for(self._wakeup, timeout=timeout)
        
    def _reload_signal(self):
        try:
            self.params.load()
            L("Reloaded.")
            self._wakeup.set()
            self._wakeup.clear()
        except self.Error, e:
            W("Problem reloading: %s" % str(e))

def setup_logging():
    logging.basicConfig(format='%(asctime)s %(message)s', 
            datefmt='%m/%d/%Y %I:%M:%S %p',
            level=logging.INFO)

def start():
    with Tempserver() as server:
        server.run()

def main():
    setup_logging()

    heredir = os.path.abspath(os.path.dirname(__file__))
    pidpath = os.path.join(heredir, 'tempserver.pid')
    pidf = lockfile.pidlockfile.PIDLockFile(pidpath, threaded=False)
    do_hup = '--hup' in sys.argv
    try:
        pidf.acquire(1)
        pidf.release()
    except (lockfile.AlreadyLocked, lockfile.LockTimeout), e:
        pid = pidf.read_pid()
        if do_hup:
            try:
                os.kill(pid, signal.SIGHUP)
                print>>sys.stderr, "Sent SIGHUP to process %d" % pid
                sys.exit(0)
            except OSError:
                print>>sys.stderr, "Process %d isn't running?" % pid
                sys.exit(1)

        print>>sys.stderr, "Locked by PID %d" % pid
    
        stale = False
        if pid > 0:
            if '--new' in sys.argv:
                try:
                    os.kill(pid, 0)
                except OSError:
                    stale = True

                if not stale:
                    print>>sys.stderr, "Stopping old tempserver pid %d" % pid
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(2)
                    pidf.acquire(0)
                    pidf.release()
            else:
                try:
                    os.kill(pid, 0)
                    # must still be running PID
                    raise e
                except OSError:
                    stale = True

        if stale:
            # isn't still running, steal the lock
            print>>sys.stderr, "Unlinking stale lockfile %s for pid %d" % (pidpath, pid)
            pidf.break_lock()

    if do_hup:
        print>>sys.stderr, "Doesn't seem to be running"
        sys.exit(1)

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
