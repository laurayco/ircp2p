import os
from daemon import EventDaemon
from service import Service

class Directory:
	def __init__(self,events,directory=None):
		directory = directory or "."
		self.directory = directory
		self.events = events
		events.listen(directory,self.handle_directory_request)
	def handle_directory_request(self,addr,event):
		if event['mode']=='read':
			if event.get('format','data')=='raw':
				self.read_raw(event)
			elif event.get('format','data')=='info':
				self.send_meta(event)
			else:
				self.read_data(event)
		elif event['mode']=='write':
			if event.get('format','data')=='raw':
				self.write_raw(event)
			else:
				self.write_data(event)
	def read_data(self,event):
		pass
	def write_data(self,event):
		pass
	def send_meta(self,event):
		pass
	def write_raw(self,event):
		pass
	def read_raw(self,event):
		pass

class DirectoryService(Service):
	def __init__(self,events):
		super().__init__(events,'directory_service')