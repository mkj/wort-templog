#!/bin/sh

# this must run as root

PIN=17
GROUP=fridgeio

echo $PIN > /sys/class/gpio/export

for f in direction value; do
    fn=/sys/devices/virtual/gpio/gpio$PIN/$f
    chgrp $GROUP $fn
    chmod g+rw $fn
done
