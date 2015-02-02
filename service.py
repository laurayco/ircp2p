from daemon import EventDaemon

class Service:
	def __init__(self,events,name,depends=None):
		self.events = events
		self.name = name
		self.depends = depends or []
		events.listen("service.discover",self.handle_service_event)
		events.listen("service.starting",self.handle_service_event)
		events.listen("service.ready",self.handle_service_event)
	def handle_service_event(self,addr,event):
		if event['event']=="service.discover":
			self.acknowledge()
		elif event['event'] == "service.starting":
			# the service has loaded,
			# but is not ready for use yet.
			pass
		elif event['event'] == "service.ready":
			self.handle_service_ready(event['service'])
	def handle_service_ready(self,service):
