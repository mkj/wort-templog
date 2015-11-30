#!/bin/sh

# this must run as root


PINS="17"

for PIN in $PINS; do
    echo $PIN > /sys/class/gpio/export
done

chgrp gpio /sys/class/gpio/gpio17/direction /sys/class/gpio/gpio17/value
chmod g+w /sys/class/gpio/gpio17/direction /sys/class/gpio/gpio17/value
