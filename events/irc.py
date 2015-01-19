import socket, signal
from queue import Queue as Q
from threading import RLock as Lock, Event, Thread
from daemon import EventDaemon

STANDARD_SOCKET = 6667

class Command:
	command_format = "{}{} {} {}\r\n"
	def __init__(self,prefix,command,args=None,trailing=None):
		self.prefix = prefix.strip() if prefix else None
		self.command = command.strip().upper()
		self.args = args or []
		self.trailing = (trailing or "").rstrip()
	@classmethod
	def from_line(cls,line):
		prefix = None
		command = None
		args = None
		trailing = None
		try:
			if line[0]==':':
				ind = line.find(" ")
				prefix = line[:ind]
				line = line[ind+1:]
			trailing_point = line.find(":")
			if trailing_point>=0:
				trailing = line[trailing_point+1:]
				line = line[:trailing_point]
			args = line.split(" ")
			command = args[0]
			args = args[1:]
			return cls(prefix,command,args or "",trailing or "")
		except Exception as e:
			print("EXCEPTION:",e)
			pass
	def compile(self):
		prefix = ""
		if self.prefix:
			prefix = self.prefix + " "
		args = " ".join(self.args)
		trailing = ":" + self.trailing if self.trailing else ""
		return self.command_format.format(prefix, self.command, args, trailing)
	def nick(self):
		assert self.prefix
		return self.prefix[1:self.prefix.find("!",1)]

class IRCBot:
	def __init__(self,nick,actual_name=None,buffer_size=1024,encoding='utf-8'):
		self.nick = nick
		self.actual_name = actual_name or nick
		self.buffer_size = buffer_size
		self.encoding = encoding
		self.command_queue = Q()
		self.life_lock = Lock()
		self.death = Event()
		self.alive = False
		self.has_started = Event()
		self.has_registered = Event()
	def get_lines(self,conn):
		while True:
			buf = b''
			try:
				buf = conn.recv(self.buffer_size)
				while len(buf)>=self.buffer_size:
					chunk = conn.recv(self.buffer_size)
					buf = buf + chunk
					if len(chunk)<self.buffer_size:
						break
			except socket.timeout:
				pass
			if len(buf)>0:
				lines = buf.split(b"\n")
				for line in lines:
					if len(line)<1:
						continue
					if line[-1]==b"\r":
						line = line[:-1]#remove the carriage return.
					if len(line)<1:
						continue
					try:
						line = line.decode(self.encoding)
						yield line
					except UnicodeDecodeError:
						yield line
			while not self.command_queue.empty():
				cmd_data = self.command_queue.get()
				conn.send(cmd_data)
	def run(self,conn):
		self.send_command(Command(None,"USER",[self.nick,"0","*"],self.actual_name))
		self.send_command(Command(None,"NICK",[self.nick]))
		try:
			for line in self.get_lines(conn):
				if not self.has_started.is_set():
					self.has_started.set()
					with self.life_lock:
						self.alive = True
				if isinstance(line,str):
					line = Command.from_line(line)
					if line:
						self.process(line)
				elif isinstance(line,bytes):
					self.process_raw(line)
				elif isinstance(line,Command):
					self.process(line)
				if not self.is_alive():
					break
		except Exception as e:
			with self.life_lock:
				self.alive = False
			raise e
		finally:
			self.death.set()
	def send_command(self,command):
		if command is None:
			return
		raw = command.compile().encode(self.encoding)
		self.command_queue.put(raw)
	def pong(self,message):
		return Command(None,"PONG",trailing=message)
	def process_raw(self, line):
		print("RAW COMMAND:",end='\n>>')
		print(line)
	def process(self,command):
		if command.command=='PING':
			self.send_command(self.pong(command.trailing))
		if not self.has_registered.is_set():
			if command.command == 'MODE':
				self.has_registered.set()
	def is_alive(self):
		with self.life_lock:
			return self.alive
	def die(self):
		with self.life_lock:
			self.alive = False
		self.death.wait()

class ChatDaemon(IRCBot):
	ignore_commands = list(map(str.strip,"""
		001 002 003 004 235
		251 252 253 254 255
		396 005 265 250 375
		NOTICE PING
	""".strip().upper().split()))
	def __init__(self,events,*a,**k):
		super().__init__(*a,**k)
		self.events = events
		self.events.listen("irc.command",self.handle_command)
	def process(self,command):
		was_registered = self.has_registered.is_set()
		if command.command not in self.ignore_commands:
			if command.command=='PRIVMSG':
				target = command.args[0]
				message = command.trailing
				print("Message received.")
				self.events.broadcast({
					"event":"irc.message",
					"from":command.nick(),
					"channel":target,
					"message":message
				})
		super().process(command)
		if not was_registered:
			if self.has_registered.is_set():
				print("Connected!")
				self.events.broadcast({
					"event":"irc.connected"
				})
	def handle_command(self,addr,data):
		if self.trust(addr):
			cmd = Command(data.get('prefix'),data['command'],data['args'],data['trailing'])
			print("IRC Command received from",data['uuid'])
			print(cmd.compile())
			self.send_command(cmd)
	def trust(self,address):
		return True

if __name__=="__main__":

	HOST_NAME = 'irc.linkandzelda.com'
	NICKNAME = 'tyler_elric'

	with EventDaemon.create_instance() as events:
		bot = ChatDaemon(events,NICKNAME)

		conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		conn.connect((HOST_NAME,STANDARD_SOCKET))
		conn.settimeout(1.0)

		bot.run(conn)