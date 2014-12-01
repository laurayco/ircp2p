import socket
from . ircbot import IRCBot as Bot, Command, STANDARD_SOCKET
from . security import keychain

class JoinCommand(Command):
	def __init__(self,channels,prefix=None):
		Command.__init__(self,prefix,"JOIN",args=[",".join(channels)])

class MessageCommand(Command):
	def __init__(self,prefix=None,args=None,message=None):
		Command.__init__(self,prefix,"PRIVMSG",args,message)

class P2PCommand(MessageCommand):
	def __init__(self,channels,command,command_args=None,prefix=None):
		command_args = " ".join(command_args) if command_args else ""
		message = ("P2P " + command + " " + command_args).strip()
		MessageCommand.__init__(self,prefix=prefix,args=channels,message=message)
		self.p2p_command = command
		self.command_args = command_args
	@classmethod
	def from_command(cls,cmd):
		message = cmd.trailing
		assert message.startswith("P2P ")
		message = message[message.find(" ")+1:].strip()
		next_space = message.find(" ")
		command = None
		command_args = None
		if next_space>=0:
			command = message[:next_space]
			message = message[next_space+1:].strip()
			command_args = message.split(" ")
		else:
			command = message
		return cls(cmd.args,command,command_args,prefix=cmd.prefix)

class NetworkBot(Bot):
	def __init__(self,keychain,nick,*a,**k):
		Bot.__init__(self,nick,*a,**k)
		self.keychain = keychain
		self.motd = ""
	def connect_to_network(self,netname):
		channel = '#' + netname
		public_key = self.keychain.public_key(netname)
		self.join(channel)
		self.introduce(netname)
	def join(self,channel):
		self.send_command(JoinCommand([channel]))
	def introduce(self,netname):
		channel = '#' + netname
		public_key = self.keychain.public_key(netname)
		cmd = P2PCommand([channel],"connect",command_args=[public_key])
		self.send_command(cmd)
	def process(self,line):
		if isinstance(line,str):
			line = Command.from_line(line)
		if isinstance(line,Command):
			if line.command=='PRIVMSG':
				target,message = line.args[0],line.trailing
				if target.lower()==self.nick.lower():
					self.handle_private_message(line,message)
				else:
					self.handle_public_message(line,target,message)
		Bot.process(self,line)
	def handle_private_message(self,line,message):
		if message.startswith("P2P "):
			self.handle_private_command(line,P2PCommand.from_command(line))
		else:
			print("[{}]:".format(line.nick()),message)
	def handle_public_message(self,line,target,message):
		target=target[1:]
		if message.startswith("P2P "):
			self.handle_public_command(line,target,P2PCommand.from_command(line))
		elif command.command=='372':
			self.motd = self.motd + command.trailing[2:] + '\n'
		elif command.command == '376':
			self.motd = self.motd[:-1].rstrip()
			print("Message of the day:")
			print(self.motd)
		else:
			print("[{}@{}]:".format(line.nick()),target,message)
	def handle_private_command(self,line,command):
		print("Private command:",command,"from",line.nick())
	def handle_public_command(self,line,target,command):
		if command.p2p_command=='connect':
			self.introduce(target)
			self.on_peer_online(command)
		elif command.p2p_command=='panic':
			self.alive = False
			self.send_command(Command(None,"QUIT",["PANIC"]))
	def on_peer_online(self,line):
		print("Peer connected:",line.command_args,"from",line.nick())
	def parse_message(self,args):
		target = args[args.find(" ")+1:]
		target = target[:target.find(":")].strip()
		if target.lower()==self.nick.lower():
			target=""
		message = args[args.find(":")+1:]
		return target, message

if __name__=="__main__":
	from threading import Thread
	from time import sleep
	HOST_NAME = 'irc.linkandzelda.com'
	NICKNAME = 'tyler_elric'
	conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	# not sure if this line is useful in client programs.
	# conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	conn.connect((HOST_NAME,STANDARD_SOCKET))
	conn.settimeout(1.0)
	keychain = Keychain()
	keychain.install_network("oras","member_alpha","SECRET_KEY",{
		"member_beta":{
			"groups":[],#known information on groups they're part of.
			"history":[]#a running record of statistics on transmissions.
		}
	})
	bot = NetworkBot(keychain,NICKNAME)
	t = Thread(target=bot.run,args=(conn,))
	t.start()
	bot.has_registered.wait()
	bot.connect_to_network("oras")