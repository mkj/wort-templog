import os
import time
import fcntl
import hmac
import binascii
import sys

import config

__all__ = ["get_csrf_blob", "check_csrf_blob", "setup_csrf"]

def get_user_hash():
    return "aaa"

def setup_csrf():
    NONCE_SIZE=16
    global _csrf_fd, _csrf_key
    _csrf_fd = open('%s/csrf.dat' % config.DATA_PATH, 'r+')

    try:
        fcntl.lockf(_csrf_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.fchmod(_csrf_fd.fileno(), 0600)
        _csrf_fd.write("%d-%s" % (os.getpid(), binascii.hexlify(os.urandom(NONCE_SIZE))))
        _csrf_fd.flush()
        _csrf_fd.seek(0)
    except IOError:
        pass
    fcntl.lockf(_csrf_fd, fcntl.LOCK_SH)
    _csrf_key = _csrf_fd.read()
    # keep the lock open until we go away


def get_csrf_blob():
    expiry = int(config.CSRF_TIMEOUT + time.time())
    content = '%s-%s' % (get_user_hash(), expiry)
    mac = hmac.new(_csrf_key, content).hexdigest()
    return "%s-%s" % (content, mac)

def check_csrf_blob(blob):
    toks = blob.split('-')
    if len(toks) != 3:
        return False

    user, expiry, mac = toks
    if user != get_user_hash():
        return False

    try:
        exp = int(expiry)
    except ValueError:
        return False

    if exp < 1000000000:
        return False

    if exp > time.time():
        return False

    check_content = "%s-%s" % (user, expiry)
    check_mac = hmac.new(_csrf_key, content).hexdigest()
    if mac == check_mac:
        return True

    return False

