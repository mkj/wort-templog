#!/usr/bin/env python3.3

import pyinotify
import glob
import sys
import fnmatch
import os

def GlobWatcher(object):
	def __init__(self, g, watcher):
		self.glob = g
		self.watches = []
		self.watcher = watcher

def add_glob(watcher, g):
	d = os.path.dirname(g)

	file_watches = add_glob_files

def main():
	touchf = sys.argv[1]

	watcher = pyinotify.WatchManager()
	dirpatterns = {}
	for g in sys.argv[2:]:
		d = os.path.dirname(g)
		pattern = os.path.basename(g)
		dirpatterns.setdefault(d, []).append(pattern)

	print(dirpatterns)

	watchpatterns = {}
	for d, patterns in dirpatterns.items():

		w = watcher.add_watch(d,
			(pyinotify.IN_MODIFY
			|pyinotify.IN_CREATE
			|pyinotify.IN_DELETE
			|pyinotify.IN_MOVED_FROM
			|pyinotify.IN_MOVED_TO))

		wd = w[d]
		watchpatterns[wd] = patterns

	def triggered(event):
		if event.name is None:
			return

		print("%s %s " % (event.name, event.maskname))
		patterns = watchpatterns[event.wd]
		for p in patterns:
			print(p)
			if fnmatch.fnmatch(event.name, p):
				print("matched %s" % p)
				os.utime(touchf, None)

	n = pyinotify.Notifier(watcher, triggered)
	n.loop()

if __name__ == '__main__':
	main()

