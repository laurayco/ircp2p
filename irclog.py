from chat import Client
from os import makedirs
from time import localtime as time, strftime
from daemon import EventDaemon
from threading import Event

joinpath = lambda x:"/".join(x)

class LoggingClient(Client):
	def __init__(self,events,directory):
		super().__init__(events)
		self.directory = directory
		self.channel_files = {}#(server,channel):filename
	def connect(self,server,port,nickname):
		makedirs(self.directory+"/"+server,exist_ok=True)
		super().connect(server,port,nickname)
	def join(self,server,channel,nick=None,port=6667):
		path = joinpath([self.directory,server,channel])
		makedirs(path,exist_ok=True)
		super().join(server,channel,nick,port)
		t = joinpath([path,strftime("%d.%m.%Y",time())+".log"])
		self.channel_files[(server,channel)] = t
		open(t,'w')
	def chat(self,server,channel,nick=None,port=6667):
		channel = channel.lower()
		self.join(server,channel,nick,port)
		fmt = "<{time:}> [{nick:}]: {message:}".format
		filename = self.channel_files[(server,channel)]
		def log_message(addr,event):
			if event['kind']=='irc':
				if event['command']=='PRIVMSG' and event['arguments'][0].lower()==channel:
					ts = strftime("%I:%M",time())
					target = event['arguments'][0]
					msg = event['trailing']
					who = event['prefix']['nick']
					with open(filename,'a') as f:
						print(fmt(nick=who,message=msg,time=ts),file=f)
		self.events.listen(server,log_message)

if __name__=="__main__":
	from sys import argv;argv = list(map(str.lower,argv[1:]))
	from threading import Event

	help = """
Useage: irclog.py [server] [channel] <nick> <port>
joins [channel] on [server]. If there
isn't a connection to [server], one is created
for you. All messages encountered are recorded
to a file (./<server>/<channel>/<timestamp>.log).
If there isn't an existing connection, or a
nickname specified, you loose.
This is a temporary interface. I plan to add a more elegant CLI.
"""

	if len(argv)<1:
		print(help)
	else:

		with EventDaemon.create_instance() as events:
			client = LoggingClient(events,"./logs")
			server = argv[0]
			channel = argv[1]
			nick = argv[2] if len(argv)>2 else None
			port = int(argv[3]) if len(argv)>3 else 6667
			client.chat(server,channel,nick,port)
			events.thread.join()