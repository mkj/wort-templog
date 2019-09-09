import re
import os
import time
import fcntl
import hmac
import sys
import hashlib

import bottle

import config

__all__ = [
    "get_csrf_blob", 
    "check_csrf_blob", 
    "setup_csrf", 
    "check_cookie",
    "init_cookie",
]

AUTH_COOKIE = 'templogauth'
AUTH_COOKIE_LEN = 16

HASH=hashlib.sha1

CLEAN_RE = re.compile('[^a-z0-9A-Z]')

def cookie_hash(c):
    return hashlib.sha256(c.encode()).hexdigest()

def init_cookie():
    """ Generates a new httponly auth cookie if required. 
    Returns the hash of the cookie (new or existing)
    """
    c = bottle.request.get_cookie(AUTH_COOKIE)
    if not c:
        c = os.urandom(AUTH_COOKIE_LEN).hex()
        years = 60*60*24*365
        bottle.response.set_cookie(AUTH_COOKIE, c, secure=True, httponly=True, max_age=10*years)
    return cookie_hash(c)

def check_cookie(allowed_users):
    c = bottle.request.get_cookie(AUTH_COOKIE)
    if not c:
        return False
    return cookie_hash(c) in allowed_users

def setup_csrf():
    NONCE_SIZE=16
    global _csrf_fd, _csrf_key
    _csrf_fd = os.fdopen(os.open('%s/csrf.dat' % config.DATA_PATH, os.O_RDWR | os.O_CREAT, 0o600), 'r+')

    try:
        fcntl.lockf(_csrf_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _csrf_fd.write("%d-%s" % (os.getpid(), os.urandom(NONCE_SIZE).hex()))
        _csrf_fd.flush()
        _csrf_fd.seek(0)
    except IOError:
        pass
    fcntl.lockf(_csrf_fd, fcntl.LOCK_SH)
    _csrf_key = _csrf_fd.read()
    # keep the lock open until we go away


def get_csrf_blob():
    expiry = int(config.CSRF_TIMEOUT + time.time())
    content = '%s-%s' % (init_cookie(), expiry)
    mac = hmac.new(_csrf_key.encode(), content.encode()).hexdigest()
    return "%s-%s" % (content, mac)

def check_csrf_blob(blob):
    toks = blob.split('-')
    if len(toks) != 3:
        return False

    user, expiry, mac = toks
    if user != init_cookie():
        return False

    try:
        exp = int(expiry)
    except ValueError:
        return False

    if exp < 1000000000:
        return False

    if exp < time.time():
        return False

    check_content = "%s-%s" % (user, expiry)
    check_mac = hmac.new(_csrf_key.encode(), check_content.encode()).hexdigest()
    if mac == check_mac:
        return True

    return False

