#!/usr/bin/env python

import params
import json
import sys
import tempfile
import signal
import os

import config


def same_type(a, b):
    ta = type(a)
    tb = type(b)

    if ta == int:
        ta = float
    if tb == int:
        tb = float

    return (ta == tb)

def main():

    i = sys.stdin.read()
    new_params = json.loads(i)

    def_params = params.Params()

    if def_params.keys() != new_params.keys():
        diff = def_params.keys() ^ new_params.keys()
        return "Mismatching params, %s" % str(diff)

    for k, v in new_params.items():
        if not same_type(v, def_params[k]):
            return "Bad type for %s" % k

    dir = os.path.dirname(config.PARAMS_FILE)

    try:
        t = tempfile.NamedTemporaryFile(prefix='config',
            dir = dir,
            delete = False)

        t.write(json.dumps(new_params, sort_keys=True, indent=4)+'\n')
        name = t.name
        t.close()

        os.rename(name, config.PARAMS_FILE)
    except Exception as e:
        return "Problem: %s" % e

    try:
        pid = int(open('%s/tempserver.pid' % dir, 'r').read())
        if pid < 2:
            return "Bad pid %d" % pid
        os.kill(pid, signal.SIGHUP)
    except Exception as e:
        return "HUP problem: %s" % e

    return 'Good Update'

if __name__ == '__main__':
    print(main())

