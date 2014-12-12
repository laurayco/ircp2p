import os
import json
import time, os

class FileUpdater:
	def __init__(self,fn):
		self.filename = fn
		self.modified = -1
	@classmethod
	def require_update(cls,f):
		def wrap(self,*a,**k):
			if self.check():
				self.update()
			return f(*a,**k)
		return wrap
	def check(self):
		return os.path.getmtime(self.filename)>self.modified
	def update(self,mode='r'):
		self.modified = os.path.getmtime(self.filename)
		with open(self.filename,mode) as f:
			return f.read()

class FileSystemMeta(FileUpdater):
	def __init__(self,filename):
		FileUpdater.__init__(self,filename)
		self.public_key = None
		self.private_key = None
		self.files = {}
		self.checkouts = {}
	def update(self):
		data = json.loads(FileUpdater.update())
		self.public_key = data['public_key']
		self.private_key = data['private_key']
		self.files = data['files']
		self.checkouts = data['checkouts']
	def save(self):
		with open(self.filename,'w') as f:
			json.dump({
				'public_key':self.public_key,
				'private_key':self.private_key,
				'checkouts':self.checkouts,
				'files':self.files
			},f)

class FileSystem:
	def __init__(self,directory,username):
		self.directory = directory
		self.username = username
		self.meta = FileSystemMeta(self.get_meta_name())
	@classmethod
	def _require_meta_(cls,fn):
		def wrap(self,*a,**k):
			if self.meta.check():
				self.meta.update()
			return fn(*a,**k)
	def full_filename(self,*fn):
		return os.path.join(self.directory,*fn)
	def get_meta_name(self):
		return self.full_filename(".meta")
	@_require_meta_
	def checkout(self,fn,duration=8600):
		if fn in self.meta.checkouts:
			if time.time()>=self.meta.checkouts[fn]['expires']:
				del self.meta.checkouts[fn]
			else:
				return False
		self.meta.checkouts[fn] = {
			'user':self.username,
			'expires':time.time() + duration
		}
		self.meta.save()