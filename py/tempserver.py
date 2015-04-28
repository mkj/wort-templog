#!/home/matt/templog/venv/bin/python

import sys
import os
import logging
import time
import signal
import asyncio
import argparse

import lockfile.pidlockfile
import daemon

import utils
from utils import L,D,EX,W
import fridge
import config
import sensor
import params
import uploader


class Tempserver(object):
    def __init__(self, test_mode):
        self.readings = []
        self.current = (None, None)
        self.fridge = None
        self._wakeup = asyncio.Event()
        self._test_mode = test_mode

    def __enter__(self):
        self.params = params.Params()
        self.fridge = fridge.Fridge(self)
        self.uploader = uploader.Uploader(self)
        self.params.load()
        self.set_sensors(sensor.make_sensor(self))
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
        runloops = [
            self.fridge.run(),
            self.sensors.run(),
            self.uploader.run(),
        ]

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(asyncio.gather(*runloops))
        except KeyboardInterrupt:
            print('\nctrl-c')
        finally:
            # loop.close() seems necessary otherwise get warnings about signal handlers
            loop.close()

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
        D("current: %s" % str(self.current))
        return self.current

    @asyncio.coroutine
    def sleep(self, timeout):
        """ sleeps for timeout seconds, though wakes if the server's config is updated """
        # XXX fixme - we should wake on _wakeup but asyncio Condition with wait_for is a bit broken? 
        # https://groups.google.com/forum/#!topic/python-tulip/eSm7rZAe9LM
        # For now we just sleep, ignore the _wakeup
        try:
            yield from asyncio.wait_for(self._wakeup.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass

    def _reload_signal(self):
        try:
            self.params.load()
            L("Reloaded.")
            self._wakeup.set()
            self._wakeup.clear()
        except Error as e:
            W("Problem reloading: %s" % str(e))

    def test_mode(self):
        return self._test_mode

def setup_logging(debug = False):
    level = logging.INFO
    if debug:
        level = logging.DEBUG
    logging.basicConfig(format='%(asctime)s %(message)s', 
            datefmt='%m/%d/%Y %I:%M:%S %p',
            level=level)
    #logging.getLogger("asyncio").setLevel(logging.DEBUG)

def start(test_mode):
    with Tempserver(test_mode) as server:
        server.run()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hup', action='store_true')
    parser.add_argument('--new', action='store_true')
    parser.add_argument('--daemon', action='store_true')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-t', '--test', action='store_true')
    args = parser.parse_args()

    setup_logging(args.debug)

    heredir = os.path.abspath(os.path.dirname(__file__))
    pidpath = os.path.join(heredir, 'tempserver.pid')
    pidf = lockfile.pidlockfile.PIDLockFile(pidpath, threaded=False)


    try:
        pidf.acquire(1)
        pidf.release()
    except (lockfile.AlreadyLocked, lockfile.LockTimeout) as e:
        pid = pidf.read_pid()
        if args.hup:
            try:
                os.kill(pid, signal.SIGHUP)
                print("Sent SIGHUP to process %d" % pid, file=sys.stderr)
                sys.exit(0)
            except OSError:
                print("Process %d isn't running?" % pid, file=sys.stderr)
                sys.exit(1)

        print("Locked by PID %d" % pid, file=sys.stderr)
    
        stale = False
        if pid > 0:
            if args.new:
                try:
                    os.kill(pid, 0)
                except OSError:
                    stale = True

                if not stale:
                    print("Stopping old tempserver pid %d" % pid, file=sys.stderr)
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
            print("Unlinking stale lockfile %s for pid %d" % (pidpath, pid), file=sys.stderr)
            pidf.break_lock()

    if args.hup:
        print("Doesn't seem to be running", file=sys.stderr)
        sys.exit(1)

    if args.daemon:
        logpath = os.path.join(os.path.dirname(__file__), 'tempserver.log')
        logf = open(logpath, 'a+')
        with daemon.DaemonContext(pidfile=pidf, stdout=logf, stderr = logf):
            start(args.test)
    else:
        with pidf:
            start(args.test)

if __name__ == '__main__':
    main()
