#!/bin/sh

# this must run as root

PINS="17"

for PIN in $PINS; do
    echo $PIN > /sys/class/gpio/export
done
