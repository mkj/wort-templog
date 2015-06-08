import os
import sys
#import ctypes
import time
import select
import logging
import binascii

D = logging.debug
L = logging.info
W = logging.warning
E = logging.error

DEFAULT_TRIES = 3
READLINE_SELECT_TIMEOUT = 1

def EX(msg, *args, **kwargs):
    kwargs['exc_info'] = True
    logging.error(msg, *args, **kwargs)

clock_gettime = None
no_clock_gettime = True
def monotonic_time():
    global clock_gettime
    global no_clock_gettime
    if no_clock_gettime:
        return time.time()

    class timespec(ctypes.Structure):
        _fields_ = [
            ('tv_sec', ctypes.c_long),
            ('tv_nsec', ctypes.c_long)
        ]
    if not clock_gettime:
        try:
            librt = ctypes.CDLL('librt.so.0', use_errno=True)
            clock_gettime = librt.clock_gettime
            clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(timespec)]
        except:
            W("No clock_gettime(), using fake fallback.")
            no_clock_gettime = True
            return time.time()
        
    t = timespec()
    CLOCK_MONOTONIC = 1 # see <linux/time.h>

    if clock_gettime(CLOCK_MONOTONIC, ctypes.pointer(t)) != 0:
        errno_ = ctypes.get_errno()
        raise OSError(errno_, os.strerror(errno_))
    return t.tv_sec + t.tv_nsec * 1e-9

# decorator, tries a number of times, returns None on failure, sleeps between
# Must be used as "@retry()" if arguments are defaulted
def retry(retries=DEFAULT_TRIES, try_time = 1):
    def inner(func):
        def new_f(*args, **kwargs):
            for i in range(retries):
                d = func(*args, **kwargs)
                if d is not None:
                    return d
                time.sleep(try_time)
            return None

        new_f.__name__ = func.__name__
        return new_f
    return inner

def readline(sock):
    timeout = READLINE_SELECT_TIMEOUT
    buf = ''
    while True:
        (rlist, wlist, xlist) = select.select([sock], [], [], timeout)
        if sock not in rlist:
            # hit timeout
            return None

        c = sock.recv(1)
        if c == '':
            # lightblue timeout
            return None
        if c == '\r':
            continue

        buf += c
        if c == '\n':
            return buf

# from http://blog.stalkr.net/2011/04/pctf-2011-32-thats-no-bluetooth.html
def crc16(buff, crc = 0, poly = 0x8408):
    l = len(buff)
    i = 0
    while i < l:
        ch = ord(buff[i])
        uc = 0
        while uc < 8:
            if (crc & 1) ^ (ch & 1):
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1
            ch >>= 1
            uc += 1
        i += 1
    return crc

def cheap_daemon():
    L("Daemonising.")
    sys.stdout.flush()
    sys.stderr.flush()
    out = file('/dev/null', 'a+')
    os.dup2(out.fileno(), sys.stdout.fileno())
    os.dup2(out.fileno(), sys.stderr.fileno())

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        E("Bad fork()")
        sys.exit(1)

    os.setsid()

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        E("Bad fork()")
        sys.exit(1)

def uptime():
    try:
        return float(open('/proc/uptime', 'r').read().split(' ', 1)[0])
    except Exception as e:
        return -1

def hexnonce():
    return binascii.hexlify(os.urandom(120))
