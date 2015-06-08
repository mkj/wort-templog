class ConfigWaiter(object):
	""" Waits for config updates from the server. http long polling """

	def __init__(self, server):
		self.server = server
		self.epoch_tag = None
		self.http_session = aiohttp.ClientSession()

	@asyncio.coroutine
	def run(self):
		# wait until someting has been uploaded (the uploader itself waits 5 seconds)
		yield from asyncio.sleep(10)
		while True:
			yield from self.do()

			# avoid spinning too fast
			yield from server.sleep(1)

	@asyncio.coroutine
	def do(self):
		try:
			if self.epoch_tag:
				headers = {'etag': self.epoch_tag}
			else:
				headers = None

	        r = yield from asyncio.wait_for(
	        	self.http_session.get(config.SETTINGS_URL, headers=headers), 
	        	300)
	        if r.status == 200:
		        resp = yield from asyncio.wait_for(r.json(), 300)

		        self.epoch_tag = resp['epoch_tag']
		        epoch = self.epoch_tag.split('-')[0]
		        if self.server.params.receive(resp['params'], epoch):
		        	self.server.reload_signal(True)

		 except Exception as e:
		 	E("Error watching config: %s" % str(e))




