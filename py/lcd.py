#!/home/matt/templog/venv/bin/python

import smbus
import time
import random
import sys

class LCD(object):

    COMMAND = 0x00
    DATA = 0x40

    def __init__(self):
        self.bus = smbus.SMBus(1)
        #self.address = 0b0111110
        self.address = 0x3e

    def setup(self):
        time.sleep(0.01)
        cmds = """0x38 function set
        0x39 function set
        0x17 freq
        0x78 # was 0x74 contrast, 101000 = 8 contrast (32 below), total 40
        0x57 # was 0x54 # power/icon/contrast, 0110 = bon, c5
        0x6a # was 0x6f follower , follow onr, rab 010 = 1.5
        0x0c on/off"""
        for l in cmds.split('\n'):
            c = eval(l.split()[0])
            self.cmd(c)

#        self.cmd(0x38)
#        self.cmd(0x39)
#        self.cmd(0x14)
#        self.cmd(0x78) # contrast
#        self.cmd(0x57) # power/icon/contrast
#        self.cmd(0x6f) # follower
#        self.cmd(0x0c)
#        self.cmd(0x01)
#        self.cmd(0x04)

    def put(self, pos, word):
        addr = 0b10000000 + (pos % 16) + (pos>=16)*40
        self.cmd(addr)
        for char in word:
            self.data(ord(char))

    def write(self, a, b):
        self.bus.write_byte_data(self.address, a, b)
        time.sleep(0.0001)
        
    def cmd(self, cmd):
        self.write(self.COMMAND, cmd)

    def data(self, data):
        self.write(self.DATA, data)

l = LCD()
l.setup()
l.put(0, 'a')
l.put(1, 'b')
l.put(4, 'b')

words = [word.strip() for word in file('/usr/share/dict/words', 'r')]
random.shuffle(words)
#words = file(sys.argv[1], 'r').read().split()

pos = 0
last = ''
for word in words:
    word = (word + ' '*16)[:16]
    #pos = (pos + 16) % 32
    #word = random.sample(words, 1)[0][:16] + ' '*16
    #char = chr(int(random.random() * 26) + ord('a'))
    l.put(0, last)
    l.put(16, word)
    last = word
    time.sleep(0.3)
