import socket
from queue import Queue as Q
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
	def __init__(self,*a,**k):
		Bot.__init__(self,nick,*a,**k)
		self.incoming_commands = Q()
	def process(self,line):
		try:
			if isinstance(line,str):
				line = Command.from_line(line)
			if isinstance(line,Command):
				self.incoming_commands.put(line)
		except:raise
		finally:
			Bot.process(line)
	def parse_message(self,args):
		target = args[args.find(" ")+1:]
		target = target[:target.find(":")].strip()
		if target.lower()==self.nick.lower():
			target=""
		message = args[args.find(":")+1:]
		return target, message