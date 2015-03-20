import os

import RPi.GPIO as GPIO

from utils import L,D,EX,W

__all__ = ["Gpio"]

class Gpio(object):
	def __init__(self, pin, name):
		self.pin = pin
		self.name = name
		GPIO.setmode(GPIO.BOARD)
		GPIO.setup(self.pin, GPIO.OUT)

	def turn(self, value):
		self.state = bool(value)
		GPIO.output(self.pin, self.state)

	def get_state(self):
		return GPIO.input(self.pin)
