#!/bin/sh

# this must run as root

PINS="17 7 24 25"
GROUP=fridgeio

for PIN in $PINS; do
    echo $PIN > /sys/class/gpio/export

    for f in direction value; do
        fn=/sys/devices/virtual/gpio/gpio$PIN/$f
        chgrp $GROUP $fn
        chmod g+rw $fn
    done
done
