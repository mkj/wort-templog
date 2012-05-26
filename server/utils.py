import os
import sys
import ctypes
import time
import select

DEFAULT_TRIES = 3

__all__ = ('monotonic_time', 'retry')

clock_gettime = None
no_clock_gettime = False
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
            print>>sys.stderr, "No clock_gettime(), using fake fallback."
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
        print "inner"
        def new_f(*args, **kwargs):
            print "newf"
            for i in range(retries):
                print "retry %d" % i
                d = func(*args, **kwargs)
                if d:
                    return d
                time.sleep(try_time)
        new_f.func_name = func.func_name
        return new_f
    return inner

def readline(sock):
    timeout = READLINE_SELECT_TIMEOUT
    buf = ''
    while true:
        (rlist, wlist, xlist) = select.select([sock], [], [], timeout)
        if sock not in rlist:
            # hit timeout
            return None

        c = sock.recv(1)
        if c == '\r':
            continue

        buf.append(c)
        if c == '\n':
            return buf

