#!/usr/bin/env python2.7

# time that the bluetooth takes to get going?
EXTRA_WAKEUP = 0

FETCH_TRIES = 3

# avoid turning off the bluetooth etc.
TESTING = False

import sys
# for wrt
sys.path.append('/root/python')
import httplib
import time
import traceback
import binascii
import hmac
import zlib
import urllib
import urllib2
import logging

L = logging.info
W = logging.warning
E = logging.error

import config

from utils import monotonic_time, retry, readline, crc16
import utils

import bluetooth

def get_socket(addr):
    s = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
    s.settimeout(1)
    s.connect((addr, 1))

    return s


@retry()
def fetch(sock):
    sock.send("fetch\n")

    crc = 0

    lines = []
    l = readline(sock)
    if l != 'START\n':
        W("Bad expected START line '%s'\n" % l.rstrip('\n'))
        return None
    crc = crc16(l, crc)

    while True:
        l = readline(sock)

        crc = crc16(l, crc)

        if l == 'END\n':
            break

        lines.append(l.rstrip('\n'))

    for d in lines:
        L("Received: %s" % d)
        
    l = readline(sock)
    recv_crc = None
    try:
        k, v = l.rstrip('\n').split('=')
        if k == 'CRC':
            recv_crc = int(v)
        if recv_crc < 0 or recv_crc > 0xffff:
            recv_crc = None
    except ValueError:
        pass

    if recv_crc is None:
        W("Bad expected CRC line '%s'\n" % l.rstrip('\n'))
        return None

    if recv_crc != crc:
        W("Bad CRC: calculated 0x%x vs received 0x%x\n" % (crc, recv_crc))
        return None

    return lines

@retry()
def turn_off(sock):
    if TESTING:
        return 99
    L("Sending btoff")
    sock.send("btoff\n");
    # read newline
    l = readline(sock)
    if not l:
        W("Bad response to btoff")
        return None

    if not l.startswith('off:'):
        W("Bad response to btoff '%s'" % l)
        return None
    off, next_wake = l.rstrip().split(':')
    L("Next wake %s" % next_wake)

    return int(next_wake)

@retry()
def clear_meas(sock):
    sock.send("clear\n");
    l = readline(sock)
    if l and l.rstrip() == 'cleared':
        return True

    E("Bad response to clear '%s'" % str(l))
    return False

def send_results(lines):
    enc_lines = binascii.b2a_base64(zlib.compress('\n'.join(lines)))
    mac = hmac.new(config.HMAC_KEY, enc_lines).hexdigest()

    url_data = urllib.urlencode( {'lines': enc_lines, 'hmac': mac} )
    con = urllib2.urlopen(config.UPDATE_URL, url_data)
    result = con.read(100)
    if result == 'OK':
        return True
    else:
        W("Bad result '%s'" % result)
        return False

def do_comms(sock):
    L("do_comms")
    d = None
    # serial could be unreliable, try a few times
    d = fetch(sock)
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

def setup_logging():
    logging.basicConfig(format='%(asctime)s %(message)s', 
            datefmt='%m/%d/%Y %I:%M:%S %p')

def main():
    setup_logging()

    L("Running templog rfcomm server")

    if '--daemon' in sys.argv:
        utils.cheap_daemon()

    while True:
        sock = None
        try:
            sock = get_socket(config.BTADDR)
        except Exception, e:
            pass
            #print>>sys.stderr, "Error connecting:"
            #traceback.print_exc(file=sys.stderr)
        next_wake_time = 0
        if sock:
            try:
                avr_wake = do_comms(sock)
                next_wake_time = time.time() + avr_wake
            except Exception, e:
                logging.exception("Error in do_comms")

        next_wake_interval = next_wake_time - time.time() - EXTRA_WAKEUP
        sleep_time = config.SLEEP_TIME
        if next_wake_interval > 0:
            sleep_time = min(next_wake_interval, sleep_time)
        L("Sleeping for %d, next wake time %f" % (sleep_time, next_wake_time))
        sleep_for(sleep_time)

if __name__ == '__main__':
    main()
