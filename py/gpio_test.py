import os

from utils import L,D,EX,W

__all__ = ["Gpio"]

class Gpio(object):
	def __init__(self, pin, name):
		self.name = name
		self.pin = name
		self.state = False
		L("Test GPIO %s pin %d started, set off." % (name, pin))

	def turn(self, value):
		self.state = bool(value)
		onoff = ("off", "on")[int(self.state)]
		L("Test GPIO %s pin %s turned %s" % (self.name, self.pin, onoff))

	def get_state(self):
		return self.state
		

	
