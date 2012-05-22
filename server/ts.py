#!/usr/bin/env python2.7

import sys
import httplib

lightblue = None
try:
    import lightblue
except ImportError:
    import bluetooth

BTADDR = "00:12:03:27:70:88"

def get_socket(addr):
    if lightblue:
        s = lightblue.socket()
        s.connect(addr, 1)
    else:
        s = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
        s.connect((addr, 1))

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


def fetch(sock):
    sock.send("fetch\n")

    def readline(self):
        buf = ''
        while true:
            c = self.recv(1)
            if c == '\r':
                continue

            buf.append(c)
            if c == '\n':
                return buf

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
