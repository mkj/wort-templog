#!/usr/bin/env python2.7

BTADDR = "00:12:03:27:70:88"
SLEEP_TIME = 180

import sys
import httplib
import time
import traceback

from utils import monotonic_time, retry

lightblue = None
try:
    import lightblue
except ImportError:
    import bluetooth

def get_socket(addr):
    if lightblue:
        s = lightblue.socket()
        s.connect(addr, 1)
    else:
        s = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
        s.connect((addr, 1))

    s.setnonblocking(True)

    return s

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


@retry()
def fetch(sock):
    sock.send("fetch\n")

    crc = 0

    lines = []
    l = readline(sock)
    if l != 'START\n':
        print>>sys.stderr, "Bad expected START line '%s'\n" % l.rstrip('\n')
        return None
    crc = crc16(l, crc)
    lines.append(l)

    while true:
        l = readline(sock)

        crc = crc16(l, crc)

        if l == 'END\n':
            break

        lines.append(l)

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
        print>>sys.stderr, "Bad expected CRC line '%s'\n" % l.rstrip('\n')
        return None

    if recv_crc != crc:
        print>>sys.stderr, "Bad CRC: calculated 0x%x vs received 0x%x\n" % (crc, recv_crc)
        return None

    return ''.join(lines)

@retry()
def turn_off(sock):
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


def do_comms(sock):
    d = None
    # serial could be unreliable, try a few times
    for i in range(FETCH_TRIES):
        d = fetch(sock)
        if d:
            break
        time.sleep(1)
    if not d:
        return

    res = send_results()
    if not res:
        return

    clear_meas(sock)

    next_wake = turn_off(sock)
    sock.close()
    return next_wake

testcount = 0

def sleep_for(secs):
    until = monotonic_time + secs
    while True:
        length = until < monotonic_time()
        if length <= 0:
            return
        time.sleep(length)

def main():

    while True:
        sock = get_socket()
        sleep_time = SLEEP_TIME
        if sock:
            next_wake = None
            try:
                next_wake = do_comms(sock)
            except Exception, e:
                print>>sys.stderr, "Error in do_comms:"
                traceback.print_last(file=sys.stderr)
            if next_wake:
                sleep_time = min(next_wake, sleep_time)

        sleep_for(sleep_time)

if __name__ == '__main__':
    main()
