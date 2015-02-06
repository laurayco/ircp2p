from daemon import EventDaemon

class Service:
	discovery_channel = 'services'
	def __init__(self,events,name,depends=None):
		self.events = events
		self.name = name
		self.depends = set(depends or [])
		self.discovered = set()
		self.status = 'starting'
		events.listen(self.discovery_channel,self.handle_service_command)
	def handle_service_event(self,addr,event):
		if event['discovery']=="discover":
			self.acknowledge()
		elif event['discovery'] == "starting":
			# the service has loaded,
			# but is not ready for use yet.
			pass
		elif event['discovery'] == "ready":
			self.handle_service_ready(event['service'])
	def initialize(self):
		self.update_status('ready')
	def acknowledge(self):
		self.broadcast({
			"discovery":self.status,
			"service":self.name
		},False)
	def update_status(self,status):
		self.status = status
		self.acknowledge()
	def handle_service_ready(self,service):
		self.discovered.add(service)
		if len(self.depends - self.discovered)<1:
			# all dependancies started and ready.
			self.initialize()
	def handle_service_command(self,addr,event):
		if event.get("service")==self.name:
			self.respond(addr,event)
		elif event['uuid']!=self.events.uuid:
			self.handle_service_event(addr,event)
	def respond(self,addr,event):
		pass
	def broadcast(self,data,locale=True):
		if locale:
			data['event']=self.name
		else:
			data['event']=self.discovery_channel
		self.events.broadcast(data)
