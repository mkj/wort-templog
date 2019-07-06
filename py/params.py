# -*- coding: utf-8 -*-
import collections
import json
import signal
import tempfile
import os
import binascii

import config
from utils import W,L,E,EX
import utils

_FIELD_DEFAULTS = {
    'fridge_setpoint': 16,
    'fridge_difference': 0.2,
    'overshoot_delay': 720, # 12 minutes
    'overshoot_factor': 1, # ºC
    'disabled': False,
    'nowort': False,
    'fridge_range_lower': 3,
    'fridge_range_upper': 3,
    }

class Params(dict):
    class Error(Exception):
        pass

    def __init__(self):
        self.update(_FIELD_DEFAULTS)
        self._set_epoch(None)

    def __getattr__(self, k):
        return self[k]

    def __setattr__(self, k, v):
        # fail if we set a bad value
        self[k]
        self[k] = v

    def _set_epoch(self, epoch):
        # since __setattr__ is overridden
        object.__setattr__(self, '_epoch', epoch)

    def _do_load(self, f):
        try:
            u = utils.json_load_round_float(f.read())
        except Exception as e:
            raise self.Error(e)

        for k in u:
            if k.startswith('_'):
                continue
            if k not in self:
                raise self.Error("Unknown parameter %s=%s in file '%s'" % (str(k), str(u[k]), getattr(f, 'name', '???')))
        self.update(u)
        # new epoch, 120 random bits
        self._set_epoch(binascii.hexlify(os.urandom(15)).decode())

        L("Loaded parameters")
        L(self.save_string())

    def load(self, f = None):
        if f:
            return self._do_load(f)
        else:
            with open(config.PARAMS_FILE, 'r') as f:
                try:
                    return self._do_load(f)
                except IOError as e:
                    W("Missing parameter file, using defaults. %s" % str(e))
                    return

    def get_epoch(self):
        return self._epoch

    def receive(self, params, epoch):
        """ updates parameters from the server. does some validation,
        writes config file to disk.
        Returns True on success, False failure 
        """

        if epoch != self._epoch:
            return

        def same_type(a, b):
            ta = type(a)
            tb = type(b)

            if ta == int:
                ta = float
            if tb == int:
                tb = float

            return ta == tb

        if self.keys() != params.keys():
            diff = self.keys() ^ params.keys()
            E("Mismatching params, %s" % str(diff))
            return False

        for k, v in params.items():
            if not same_type(v, self[k]):
                E("Bad type for %s" % k)
                return False

        dir = os.path.dirname(config.PARAMS_FILE)
        try:
            t = tempfile.NamedTemporaryFile(prefix='config',
                mode='w+t', # NamedTemporaryFile is binary by default
                dir = dir,
                delete = False)

            out = json.dumps(params, sort_keys=True, indent=4)+'\n'
            t.write(out)
            name = t.name
            t.close()

            os.rename(name, config.PARAMS_FILE)
        except Exception as e:
            EX("Problem: %s" % e)
            return False

        self.update(params)
        L("Received parameters")
        L(self.save_string())
        return True

    def save_string(self):
        return json.dumps(self, sort_keys=True, indent=4)
