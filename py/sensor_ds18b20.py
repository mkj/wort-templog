#!/usr/bin/env python2.7

import gevent
import config
import re
from utils import L,W,E,EX

class DS18B20s(gevent.Greenlet):

    THERM_RE = re.compile('.* YES\n.*t=(.*)\n', re.MULTILINE)

    def __init__(self, server):
        gevent.Greenlet.__init__(self)
        self.server = server
        # XXX set up paths
        # XXX set up drain etc

    def _run(self):
        while True:
            self.do()
            gevent.sleep(config.SENSOR_SLEEP)

    def sensor_path(self, s):
        return os.path.join(self.master_dir, s)

    def do_sensor_name(self, s, contents = None):
        try:
            if contents is None:
                fn = os.path.join(self.sensor_path(s), 'w1_slave')
                f = open(fn, 'r')
                contents = f.read()
            match = self.THERM_RE.match(contents)
            if match is None:
                return None
            temp = int(match.groups(1)[0])
            return temp / 1000.0
        except Exception, e:
            EX("Problem reading sensor '%s': %s" % (s, str(e)))
            return None

    def do(self):
        vals = {}
        for n in self.sensor_names():
                value = do_sensor(n)
                if value is not None:
                    vals[n] = value

        self.server.add_reading(vals)

    def sensor_names(self):
        """ Returns a sequence of sensorname """
        return [d for d in os.listdir(self.master_dir) if
            os.stat(sensor_path(d)).st_mode & stat.S_ISDIR]

    def wort_name(self):
        return config.WORT_NAME

    def fridge_name(self):
        return config.FRIDGE_NAME
