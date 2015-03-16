import socket
from selectors import DefaultSelector, EVENT_READ, EVENT_WRITE
from threading import Event
from re import compile as Regex
from daemon import EventDaemon
from service import Service

class ChatServerInterface(Service):
	ENCODING = 'utf-8'
	BUFFER_SIZE = 1024
	REGEX = Regex(r'^(?::(?P<prefix>\S+)\s+)?(?P<command>\w+)\s*(?P<arguments>[^:]*)\s*(?::(?P<trailing>.*))?$')
	PREFIX_REGEX = Regex(r'')
	outgoing_data = b''
	incoming_data = b''
	has_identified = False
	has_connected = False
	def __init__(self,host,nick,events):
		super().__init__(events,host,['irc'])
		self.nick = nick
		self.events = events
	def respond(self,addr,command):
		prefix = command.get("prefix",None)
		trailing = command.get("trailing",None)
		arguments = command.get("arguments",[])
		command = command['command']
		self.enqueue_message(command,trailing=trailing,prefix=prefix,args=arguments)
	def write_data(self,sock):
		if len(self.outgoing_data)>0:
			sock.send(self.outgoing_data)
			self.outgoing_data = b''
	def read_data(self,sock):
		if not self.has_connected:
			self.has_connected = True
			self.broadcast({
				'kind':"info",
				'meta':{
					'event':'connected'
				}
			})
		bs = self.BUFFER_SIZE
		data = sock.recv(bs)
		while len(data)>=bs:
			self.incoming_data = self.incoming_data + data
			data = sock.recv(bs)
		self.incoming_data = self.incoming_data + data
		last_line = self.incoming_data.find(b"\n",1)
		while last_line>=0:
			line = self.incoming_data[:last_line]
			try:
				line = line.decode(self.ENCODING).strip()
				print(line)
				self.process(line)
			except:
				print("Unable to process line:\n->",line)
			self.incoming_data = self.incoming_data[last_line+1:]
			last_line = self.incoming_data.find(b"\n")
		if not self.has_identified:
			self.enqueue_message("NICK",args=[self.nick])
			self.enqueue_message("USER",args=[self.nick,"0","*"],trailing=self.nick)
	def parse_prefix(self,prefix):
		excite = prefix.find("!")
		nick = prefix
		where = None
		user = None
		if excite>=0:
			nick = prefix[:excite]
			where = prefix.find("@",excite)
			if where >= 0:
				user = prefix[excite+1:where]
				where = prefix[where+1:]
			else:
				user = prefix[excite+1:]
				where = None
		else:
			where = None
			user = None
		return {
			'nick':nick,
			'user':user,
			'host':where
		}
	def enqueue_message(self,command,trailing=None,prefix=None,args=None):
		print("Sending message:\n->",command,*(args if args else []))
		msg = self.build_message(command,trailing=trailing,prefix=prefix,args=args)
		self.outgoing_data = self.outgoing_data + msg
	def process(self,line):
		m = self.REGEX.match(line)
		if m:
			prefix = m.group("prefix")
			r = {
				"kind":"irc",
				'prefix':self.parse_prefix(prefix) if prefix else None,
				'command':m.group('command'),
				'arguments':list(map(str.strip,m.group('arguments').split())),
				'trailing':m.group("trailing")
			}
			if r['command']=='PING':
				self.enqueue_message("PONG",trailing=r['trailing'])
			else:
				if r['command']=='001':
					self.broadcast({
						"kind":'info',
						"meta":{
							"event":"identified"
						}
					})
					self.has_identified = True
				self.broadcast(r)
	def build_message(self,command,trailing=None,prefix=None,args=None):
		args = args or []
		prefix = prefix or ""
		trailing = ":"+trailing if trailing else ""
		return ("{} {} {} {}".format(prefix,command," ".join(args),trailing).strip()+"\r\n").encode(self.ENCODING)

class IRC(Service):
	DEFAULT_PORT = 6667
	TIMEOUT = 3
	def __init__(self,events):
		super().__init__(events,'irc')
		self.servers = set()
		self.selector = DefaultSelector()
		self.events = events
		self.has_servers = Event()
		self.channels = {}#server:[channels]
	def respond(self,addr,command):
		if command['action']=='connect':
			server = command['host']
			nick = command['nick']
			port = command.get('port',self.DEFAULT_PORT)
			self.connect((server,port),nick)
		if command['action']=='status':
			print(self.servers)
			self.broadcast({
				'kind':'status',
				'status':{
					'servers':{
						s: {
							'channels':v
						} for s,v in self.channels.items()
					}
				}
			})
	def connect(self,addr,nick):
		host = addr[0]
		if host not in self.servers:
			print(nick)
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			print(addr)
			sock.connect(addr)
			self.events.listen(host,self.check_channels)
			self.selector.register(sock,EVENT_READ|EVENT_WRITE,ChatServerInterface(addr[0],nick,self.events))
			self.servers.add(host)
			self.channels[host] = list()
			if not self.has_servers.is_set():
				self.has_servers.set()
	def check_channels(self,addr,event):
		if event['kind']=='irc':
			if event['command']=='332':
				print(event['event'],event['arguments'])
				self.channels[event['event']].append(event['arguments'][1].lower())
	def loop(self):
		while True:
			self.has_servers.wait()
			for key,mask in self.selector.select():
				if mask&EVENT_READ==EVENT_READ:
					key.data.read_data(key.fileobj)
				if mask&EVENT_WRITE==EVENT_WRITE:
					key.data.write_data(key.fileobj)

if __name__ == "__main__":
	with EventDaemon.create_instance() as events:
		irc_daemon = IRC(events)
		irc_daemon.initialize()
		irc_daemon.loop()
