import os
import time
import fcntl
import sys

class AtomicFile(object):
    DELAY = 0.5
    def __init__(self, name):
        self.name = name

    def write(self, data, timeout = 5):
        try:
            end = time.time() + timeout
            with open(self.name, "r+") as f:
                while timeout == 0 or time.time() < end:
                    try:
                        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except IOError:
                        time.sleep(DELAY)
                        continue

                    os.ftruncate(f.fileno(), 0)
                    f.write(data)
                    return True

        except IOError as e:
            print(e, file=sys.stderr)

        return False

    def read(self, timeout = 5):
        try:
            end = time.time() + timeout
            with open(self.name, "r") as f:
                while timeout == 0 or time.time() < end:
                    try:
                        fcntl.lockf(f, fcntl.LOCK_SH | fcntl.LOCK_NB)
                    except IOError:
                        time.sleep(DELAY)
                        continue

                    return f.read()

        except IOError as e:
            print(e, file=sys.stderr)

        return None
