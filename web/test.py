#!/usr/bin/env python
import time
import struct
import sys
import binascii

def convert_ds18b20_12bit(reading):
    value = struct.unpack('>h', binascii.unhexlify(reading))[0]
    return value * 0.0625

if __name__ == '__main__':
    print convert_ds18b20_12bit(sys.argv[1])
