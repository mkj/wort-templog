#!/usr/bin/env python2.7

import os
import re

import gevent
import gevent.threadpool

import config
from utils import D,L,W,E,EX

class DS18B20s(gevent.Greenlet):

    THERM_RE = re.compile('.* YES\n.*t=(.*)\n', re.MULTILINE)

    def __init__(self, server):
        gevent.Greenlet.__init__(self)
        self.server = server
        self.readthread = gevent.threadpool.ThreadPool(1)
        self.master_dir = config.SENSOR_BASE_DIR

    def _run(self):
        while True:
            self.do()
            gevent.sleep(config.SENSOR_SLEEP)

    def read_wait(self, f):
        # handles a blocking file read with a gevent threadpool. A
        # real python thread performs the read while other gevent
        # greenlets keep running.
        # the ds18b20 takes ~750ms to read, which is noticable
        # interactively.
        return self.readthread.apply(f.read)

    def do_sensor(self, s, contents = None):
        """ contents can be set by the caller for testing """
        D("dosensor %s" % s)
        try:
            if contents is None:
                fn = os.path.join(self.master_dir, s, 'w1_slave')
                f = open(fn, 'r')
                contents = self.read_wait(f)

            match = self.THERM_RE.match(contents)
            if match is None:
                D("no match")
                return None
            temp = int(match.groups(1)[0]) / 1000.0
            D("returning %f" % temp)
            return temp
        except Exception, e:
            EX("Problem reading sensor '%s': %s" % (s, str(e)))
            return None

    def do(self):
        vals = {}
        for n in self.sensor_names():
                value = self.do_sensor(n)
                if value is not None:
                    vals[n] = value

        self.server.add_reading(vals)

    def sensor_names(self):
        """ Returns a sequence of sensorname """
        slaves_path = os.path.join(self.master_dir, "w1_master_slaves")
        names = open(slaves_path, 'r').read().split()
        D("returning names %s" % names)
        return names

    def wort_name(self):
        return config.WORT_NAME

    def fridge_name(self):
        return config.FRIDGE_NAME
