import logging
import socket
import threading
import json
import struct

class EventNode:
	BUFFER_SIZE = 1024
	def __init__(self,sock,addr,uuid=None):
		self.addr = addr
		self.sock = sock
		self.uuid = uuid or self.make_uuid()
		self.running = False
		self.subscriptions = {}# event:set(handlers)
		self.data_buffer = {}# addr:[bytes]
	def run(self):
		self.running = True
		while self.running:
			data,addr = self.sock.recvfrom(self.BUFFER_SIZE)
			finished = len(data)<self.BUFFER_SIZE
			data = self.enqueue_data(addr,data)
			if finished:
				self.process_complete_data(addr,data)
				del self.data_buffer[addr]
	def enqueue_data(self,addr,data):
		if addr in self.data_buffer:
			data = self.data_buffer[addr] + data
		self.data_buffer[addr] = data
		return self.data_buffer[addr]
	def process_complete_data(self,addr,data):
		data = data.decode('utf-8')
		data = json.loads(data)
		if data['uuid'] != self.uuid:
			self._emit_(addr,data['event'],data)
	def _emit_(self,addr,event,data):
		print("delegating",event)
		for listener in self.subscriptions.get(event,[]):
			listener(addr,data)
	def broadcast(self,data):
		data["uuid"] = self.uuid
		print("broadcasting",data['event'])
		data = json.dumps(data).encode('utf-8')
		self.sock.sendto(data,self.addr)
	def listen(self,event,handler):
		if event in self.subscriptions:
			self.subscriptions[event].add(handler)
		else:
			self.subscriptions[event] = set([handler])
	@classmethod
	def create_socket(cls,addr,ttl=20,mc_loop=1):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR, 1)
		try:
			sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEPORT, 1)
		except:
			pass
		mreq = struct.pack("=4sl", socket.inet_aton(addr[0]), socket.INADDR_ANY)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
		sock.bind(('',addr[1]))
		return sock
	@classmethod
	def create_instance(cls,addr=("224.1.1.1",5007),ttl=20,mc_loop=1,uuid=None):
		return cls(cls.create_socket(addr,ttl,mc_loop),addr,uuid)
	@classmethod
	def make_uuid(cls):
		return 'uuid'

class EventDaemon(EventNode):
	def __init__(self,*a,**k):
		super().__init__(*a,**k)
		self.thread = threading.Thread(target=self.run)
		self.thread.daemon = True
	@classmethod
	def create_instance(cls,addr=("224.1.1.1",5007),ttl=20,mc_loop=1,uuid=None):
		return cls(cls.create_socket(addr,ttl,mc_loop),addr,uuid)
	def __enter__(self):
		self.thread.start()
		return self
	def __exit__(self,type,value,trace):
		self.running = False
		self.sock.close()
