
class Service:
	status = None
	def __init__(self,events,name,dependancies):
		self.events = events
		self.name = name
		self.requires = set(dependancies)
		self.resolved = set()
	def get_greeting(self): return {
		"event":"service.greet",
		"name":self.name,
		"status":self.status
	}
	def start(self):
		self.status = "starting"
		self.events.listen("service.greet",self.checkin)
		greeting = self.get_greeting()
		greeting["needs"] = self.requires
		self.events.broadcast(greeting)
	def checkin(self,addr,data):
		remaining = self.requires - self.resolved
		greeting = None
		if data['name'] in remaining:
			self.resolved.add(data['name'])
			if len(remaining)<2:
				# all dependancies available.
				self.status = "ready"
				greeting = self.get_greeting()
		if self.name in data.get("needs",[]):
			if greeting is None:
				greeting = self.get_greeting()
		if greeting:
			self.events.broadcast(greeting)
