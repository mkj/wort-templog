import os
import sys
import ctypes
import time
import select
import logging
import binascii
import json
import datetime
import collections

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


def json_load_round_float(s, **args):
    return json.loads(s,parse_float = lambda f: round(float(f), 2), **args)

class NotTooOften(object):
    """ prevents things happening more than once per limit.
    Isn't monotonic, good enough for logging. eg
    self.logfailure = NotTooOften(180) # 3 minutes
    ...
    if self.logfailure():
        L("blah")
    """
    def __init__(self, limit):
        """ limit is a delay in seconds or TimeDelta """
        if type(limit) is datetime.timedelta:
            self.limit = limit
        else:
            self.limit = datetime.timedelta(seconds=limit)

        # must be positive
        assert self.limit > datetime.timedelta(0)
        self.last = datetime.datetime(10, 1, 1)

    def __call__(self):
        if datetime.datetime.now() - self.last > self.limit:
            self.last = datetime.datetime.now()
            return True

    def log(self, msg):
        """ calls L(msg) if it isn't too often, otherwise D(msg)
        """
        if self():
            L(msg + " (log interval %s)" % str(self.limit))
        else:
            D(msg)

Period = collections.namedtuple('Period', 'start end')
class StepIntegrator(object):
    """
    Takes on/off events and a monotonically increasing timefn. Returns the integral 
    of (now-limittime, now) over those events.

    >>> s = StepIntegrator(lambda: t, 40)
    >>> t = 1
    >>> s.turn(1)
    >>> t = 10
    >>> s.turn(0)
    >>> t = 20
    >>> s.turn(1)
    >>> t = 30
    >>> print(s.integrate())
    19
    >>> s.turn(0)
    >>> print(s.integrate())
    19
    >>> t = 35
    >>> print(s.integrate())
    19
    >>> t = 42
    >>> print(s.integrate())
    18
    >>> t = 52
    >>> print(s.integrate())
    10
    >>> t = 69
    >>> print(s.integrate())
    1
    >>> t = 70
    >>> print(s.integrate())
    0
    >>> t = 170
    >>> print(s.integrate())
    0
    """
    def __init__(self, timefn, limittime):
        # _on_periods is a list of [period]. End is None if still on
        self._on_periods = []
        self._timefn = timefn
        self._limittime = limittime

    def set_limit(self, limittime):
        if self._limittime == limittime:
            return
        self._limittime = limittime
        self._trim()

    def turn(self, value):
        if not self._on_periods:
            if value:
                self._on_periods.append(Period(self._timefn(), None))
            return

        # state hasn't changed
        on_now = (self._on_periods[-1].end is None)
        if value == on_now:
            return

        if value:
            self._on_periods.append(Period(self._timefn(), None))
        else:
            self._on_periods[-1] = self._on_periods[-1]._replace(end = self._timefn())

    def _trim(self):
        begin = self._timefn() - self._limittime
        # shortcut, first start is after begin
        if not self._on_periods or self._on_periods[0].start >= begin:
            return

        new_periods = []
        for s, e  in self._on_periods:
            if s == e:
                continue
            elif s >= begin:
                new_periods.append(Period(s,e))
            elif e is not None and e < begin:
                continue
            else:
                new_periods.append(Period(begin, e))
        self._on_periods = new_periods

    def integrate(self):
        self._trim()
        tot = 0
        for s, e in self._on_periods:
            if e is None:
                e = self._timefn()
            tot += (e-s)
        return tot







