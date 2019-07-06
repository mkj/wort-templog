import os

from utils import L,D,EX,W

__all__ = ["Gpio"]

class Gpio(object):
    SYS_GPIO_BASE = '/sys/class/gpio/gpio'
    def __init__(self, pin, name):
        self.pin = pin
        self.name = name

        dir_fn = '%s%d/direction' % (self.SYS_GPIO_BASE, pin)
        with open(dir_fn, 'w') as f:
            # make sure it doesn't start "on"
            f.write('low')
        val_fn = '%s%d/value' % (self.SYS_GPIO_BASE, pin)
        self.value_file = open(val_fn, 'r+')

    def turn(self, value):
        self.value_file.seek(0)
        self.value_file.write('1' if value else '0')
        self.value_file.flush()

    def get_state(self):
        self.value_file.seek(0)
        buf = self.value_file.read().strip()
        if buf == '0':
            return False
        if buf != '1':
            E("Bad value read from gpio '%s': '%s'" 
                % (self.value_file.name, buf))
        return True


def main():
    g = Gpio(17, 'f')
    g.turn(1)

    print(g.get_state())

    g.turn(0)

    print(g.get_state())

if __name__ == '__main__':
    main()
