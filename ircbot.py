import socket, signal
from queue import Queue as Q
from threading import RLock as Lock, Event

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
			# receive all server commands.
			buf = b''
			try:
				buf = conn.recv(self.buffer_size)
				# if the condition is true the first time
				# it will be true for all consecutive iterations.
				# the loop must break from inside the body.
				while len(buf)>=self.buffer_size:
					chunk = conn.recv(self.buffer_size)
					buf = buf + chunk
					if len(chunk)<self.buffer_size:
						break
			except socket.timeout:
				pass
			# all available server commands have
			# been received.
			# now we process them.
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
			# now that we've processed all the server commands
			# we send back all generated responses.
			# since we're using a queue, this is thread-friendly
			# meaning you can send commands that weren't generated
			# inside this thread, as well as responses generated
			# inside this thread.
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

if __name__=="__main__":
	from threading import Thread

	HOST_NAME = 'irc.linkandzelda.com'
	NICKNAME = 'tyler_elric'

	class ChatBot(IRCBot):
		msg_string = "[{}@{}]: {}".format
		ignore_commands = list(map(str.strip,"""
			001 002 003 004 235
			251 252 253 254 255
			396 005 265 250 375
			NOTICE PING
		""".strip().upper().split()))
		def __init__(self,*a,**k):
			IRCBot.__init__(self,*a,**k)
			self.message_of_the_day = ''
		def process(self,command):
			if command.command=='PRIVMSG':
				target = command.args[command.args.find(" ")+1:]
				target = target[:target.find(":")].strip()
				if target.lower()==self.nick.lower():
					target=""
				message = command.args[command.args.find(":")+1:]
				print(self.msg_string(command.nick(),target,message))
			elif command.command=='372':
				self.message_of_the_day = self.message_of_the_day + command.trailing[2:] + '\n'
			elif command.command == '376':
				self.message_of_the_day = self.message_of_the_day[:-1].rstrip()
				print("Message of the day:")
				print(self.message_of_the_day)
			elif command.command in self.ignore_commands:
				pass
			else:
				print(command.compile())
			IRCBot.process(self,command)

	def threadsafe_function(f):
		l = Lock()
		def w(*a,**k):
			with l:
				f(*a,**k)
		w.lock = l
		return w

	def signal_handler(sig):
		def w(f):
			def h(*a,**kw):
				return f(*a,**kw)
			signal.signal(sig,h)
			return h
		return w

	#@signal_handler(signal.SIGALRM)
	def timeout_handler(signal,frame):
		raise RuntimeError("Timeout!")

	def timeout_function(timeout):
		def w(f):
			def h(*a,**k):
				#signal.alarm(timeout)
				x = f(*a,**k)
				#signal.alarm(0)
				return x
			return h
		return w

	#prevent server output from interfering with stdin prompts.
	print = threadsafe_function(print)
	input = timeout_function(10)(input)

	bot = ChatBot(NICKNAME)
	conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	# not sure if this line is useful in client programs.
	#conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	conn.connect((HOST_NAME,STANDARD_SOCKET))
	conn.settimeout(1.0)
	t = Thread(target=bot.run,args=(conn,),daemon=True)
	t.start()
	cmd = ''
	bot.has_started.wait()
	bot.has_registered.wait()
	while bot.is_alive() and cmd.lower()!='/quit':
		cmd = input(">")
		if cmd.lower() != '/quit':
			bot.send_command(Command.from_line(cmd))
