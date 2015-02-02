import os
from daemon import EventDaemon
from service import Service

class Directory:
	def __init__(self,events,directory=None):
		directory = directory or "."
		self.directory = directory
	def process(self,event):
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
	def get_filename(self,event):
		base_filename = event['filename']
		base_directory = os.path.abspath(self.directory)
		return os.path.join(base_directory,base_filename)
	def open_file(self,event):
		rw = 'r' if event.get('mode','read')=='read' else 'w'
		return open(self.get_filename(event),rw)
	def read_data(self,event):
		with self.open_file(event) as f:
			data = json.load(f)
	def read_raw(self,event):
		with self.open_file(event) as f:
			data = f.read()
	def send_meta(self,event):
		filename = self.get_filename(event)
	def write_data(self,event):
		with self.open_file(event) as f:
			pass
	def write_raw(self,event):
		with self.open_file(event) as f:
			pass

class DirectoryService(Service):
	def __init__(self,events):
		super().__init__(events,'directory_service')
		self.open_directories = {}
	def respond(self,addr,event):
		if event['directory'] not in self.open_directories:
			self.open_directories = self.spawn_directory(event)
		directory = self.open_directories[event['directory']]
		result = directory.process(event)
		if result:
			self.emits.broadcast(result)
	def spawn_directory(self,event):
		return Directory(event['directory'])
