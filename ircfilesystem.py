from daemon import EventDaemon
from service import Service

class IRCFilesystem(Service):
	def __init__(self,events):
		super().__init__(events,'ircfs',depends=['irc','directory_service'])
	def respond(self,addr,event):
		# google-docs-esque api.
		# write-only for irc service.
		# read from events
		# respond to requests for data,
		pass
	