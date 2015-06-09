import gevent
import fcntl
import hashlib

import binascii
import os

class Settings(object):
    RAND_SIZE = 15 # 120 bits

    """ Handles state updates from both the web UI and from the fridge client.
    The fridge client is canonical. It provides the epoch (apart from 'startepoch'), that
    is changed any time the fridge reloads its local config. The fridge only accepts
    updates that have the same epoch.

    When the web UI changes it keeps the same epoch but generates a new tag. The fridge sends
    its current known tag and waits for it to change.

    content is opaque, presently a dictionary of decoded json 
    """

    def __init__(self):
        self.event = gevent.event.Event()
        self.contents = None
        self.epoch = None
        self.tag = None

        self.update(None, 'startepoch')

    def wait(self, epoch_tag = None, timeout = None):
        """ returns false if the timeout was hit """
        if self.epoch_tag() != epoch_tag:
            # has alredy changed
            return True
        return self.event.wait(timeout)

    def epoch_tag(self):
        return '%s-%s' % (self.epoch, self.tag)

    def random(self):
        return binascii.hexlify(os.urandom(self.RAND_SIZE))

    def update(self, contents, epoch = None):
        """ replaces settings contents and updates waiters if changed """
        if epoch:
            if self.epoch == epoch:
                return
            else:
                self.epoch = epoch

        self.tag = self.random()
        self.contents = contents

        self.event.set()
        self.event.clear()

    def get(self):
        """ Returns (contents, epoch-tag) """
        return self.contents, self.epoch_tag()





