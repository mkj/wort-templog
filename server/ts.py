#!/usr/bin/env python2.7

BTADDR = "00:12:03:27:70:88"
SLEEP_TIME = 180
# time that the bluetooth takes to get going?
EXTRA_WAKEUP = 0

FETCH_TRIES = 3

# avoid turning off the bluetooth etc.
TESTING = True

import sys
# for wrt
sys.path.append('/root/python')
import httplib
import time
import traceback
import binascii
import hmac

import config

from utils import monotonic_time, retry, readline, crc16

lightblue = None
try:
    import lightblue
except ImportError:
    import bluetooth

def get_socket(addr):
    if lightblue:
        s = lightblue.socket()
        s.connect((addr, 1))
        s.settimeout(3)
    else:
        s = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
        s.connect((addr, 1))

    s.setblocking(False)

    return s


@retry()
def fetch(sock):
    print "fetch"
    sock.send("fetch\n")

    crc = 0

    lines = []
    l = readline(sock)
    if l != 'START\n':
        print>>sys.stderr, "Bad expected START line '%s'\n" % l.rstrip('\n')
        return None
    crc = crc16(l, crc)
    lines.append(l)

    while True:
        l = readline(sock)

        crc = crc16(l, crc)

        if l == 'END\n':
            break

        lines.append(l.rstrip('\n'))

    print lines

    l = readline(sock)
    recv_crc = None
    try:
        k, v = l.rstrip('\n').split('=')
        print k,v
        if k == 'CRC':
            recv_crc = int(v)
        if recv_crc < 0 or recv_crc > 0xffff:
            recv_crc = None
    except ValueError:
        pass

    if recv_crc is None:
        print>>sys.stderr, "Bad expected CRC line '%s'\n" % l.rstrip('\n')
        return None

    if recv_crc != crc:
        print>>sys.stderr, "Bad CRC: calculated 0x%x vs received 0x%x\n" % (crc, recv_crc)
        return None

    return lines

@retry()
def turn_off(sock):
    if TESTING:
        return None
    sock.send("btoff\n");
    # read newline
    l = readline(sock)
    if not l:
        print>>sys.stderr, "Bad response to btoff\n"
        return None

    off, next_wake = l.rstrip().split(':')
    if off != 'Off':
        print>>sys.stderr, "Bad response to btoff '%s'\n" % l

    return int(next_wake)

def send_results(lines):
    enc_lines = binascii.b2a_base64('\n'.join(lines))
    hmac.new(config.HMAC_KEY, enc_lines).hexdigest()

    url_data = urllib.url_encode( ('lines', enc_lines), ('hmac', mac) )
    con = urllib2.urlopen(config.UPDATE_URL, url_data)


def do_comms(sock):
    print "do_comms"
    d = None
    # serial could be unreliable, try a few times
    for i in range(FETCH_TRIES):
        d = fetch(sock)
        if d:
            break
        time.sleep(1)
    if not d:
        return

    res = send_results(d)
    if not res:
        return

    clear_meas(sock)

    next_wake = turn_off(sock)
    sock.close()
    return next_wake

testcount = 0

def sleep_for(secs):
    until = monotonic_time() + secs
    while True:
        length = until - monotonic_time()
        if length <= 0:
            return
        time.sleep(length)

def main():

    while True:
        sock = None
        try:
            sock = get_socket(BTADDR)
        except Exception, e:
            print>>sys.stderr, "Error connecting:"
            traceback.print_exc(file=sys.stderr)
        sleep_time = SLEEP_TIME
        if sock:
            next_wake = None
            try:
                next_wake = do_comms(sock)
            except Exception, e:
                print>>sys.stderr, "Error in do_comms:"
                traceback.print_exc(file=sys.stderr)
            if next_wake:
                sleep_time = min(next_wake+EXTRA_WAKEUP, sleep_time)

        if TESTING:
            print "Sleeping for %d" % sleep_time
        sleep_for(sleep_time)

if __name__ == '__main__':
    main()
