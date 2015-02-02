from daemon import EventDaemon
from threading import Event
from time import localtime as time, strftime

class Client:
	def __init__(self,events):
		self.events = events
		self.status = None
		self.received_status = Event()
	def get_status(self,server):
		if self.status:
			return self.status
		else:
			def on_received_status(addr,event):
				if event['event']=='irc.status':
					self.status = event['status']
					self.received_status.set()
			self.events.listen('irc.status',on_received_status)
			self.events.broadcast({
				'event':'irc.command',
				'action':'status'
			})
			self.received_status.wait()
			self.events.unlisten(server,on_received_status)
			return self.status
	def connect(self,server,port,nickname):
		status = self.get_status(server)
		connected_servers = set(status['servers'])
		if server in connected_servers:
			return
		e = Event()
		def wait_for_server(addr,event):
			if event['kind']=='info':
				if event['meta']['event']=='identified':
					self.status['servers'][server] = {
						'channels':[]
					}
					e.set()
		self.events.listen(server,wait_for_server)
		self.events.broadcast({
			'nick':nickname,
			'event':'irc.command',
			'action':'connect',
			'host':server
		})
		e.wait()
		self.events.unlisten(server,wait_for_server)#chat chat irc.linkandzelda.com #gogo metalbot
	def join(self,server,channel,nick=None,port=6667):
		channel = channel.lower()
		self.connect(server,port,nick)
		status = self.get_status(server)
		connected_servers = set(status['servers'])
		if not server in connected_servers:
			print("Not connected...")
		if channel in set(status['servers'][server]['channels']):
			print("Joined already.")
			return
		else:
			print("Joining",channel)
			e = Event()
			def channel_joined(addr,event):
				if event['kind']=='irc':
					if event['command']=='JOIN':
						if event['trailing'].lower()==channel:
							status['servers'][server]['channels'].append(channel)
							self.events.unlisten(server,channel_joined)
							e.set()
			self.events.listen(server,channel_joined)
			self.events.broadcast({
				'event':'irc.command:'+server,
				'command':"JOIN",
				"arguments":[channel]
			})
			e.wait()
	def chat(self,server,channel,nick=None,port=6667):
		channel = channel.lower()
		self.join(server,channel,nick,port)
		fmt = "<{time:}> [{nick:}]: {message:}".format
		def log_message(addr,event):
			if event['kind']=='irc':
				if event['command']=='PRIVMSG' and event['arguments'][0].lower()==channel:
					ts = strftime("%I:%M",time())
					target = event['arguments'][0]
					msg = event['trailing']
					who = event['prefix']['nick']
					print(fmt(nick=who,message=msg,time=ts))
		self.events.listen(server,log_message)

if __name__=="__main__":
	from sys import argv;argv = list(map(str.lower,argv[1:]))

	help = """
Useage: chat.py ...
  connect [nick] [server] <port> - establishes a connection to [server],
                            optionally on port <port> (defaults to 6667)
  chat [server] [channel] <nick> <port> - joins [channel] on [server]. If there
                            isn't a connection to [server], one is created
                            for you. then an interactive console is made
                            so you are able to send and receive messages.
                            If there isn't an existing connection, or a
                            nickname specified, you loose.
  join [server] [channel] <nick> <port> - joins [channel] on [server]. There
                            is no interactive chat console. The only real
                            use for this is if you have another script
                            monitoring a server / channel for events.
                            If there isn't an existing connection, or a
                            nickname specified, you loose.
  This is a temporary interface. I plan to add a more elegant CLI.
"""

	if len(argv)<1:
		print(help)
	else:

		with EventDaemon.create_instance() as events:
			client = Client(events)
			if argv[0]=='connect':
				nick = argv[1]
				server = argv[2]
				port = int(argv[3]) if len(argv)>3 else 6667
				client.connect(server,port,nick)
			elif argv[0] == 'join':
				server = argv[1]
				channel = argv[2]
				nick = argv[3] if len(argv)>3 else None
				port = int(argv[4]) if len(argv)>4 else 6667
				client.join(server,channel,nick,port)
			elif argv[0] == 'chat':
				server = argv[1]
				channel = argv[2]
				nick = argv[3] if len(argv)>3 else None
				port = int(argv[4]) if len(argv)>4 else 6667
				client.chat(server,channel,nick,port)
				events.thread.join()
