import os
import json
import time

class FileSystem:
	def __init__(self,directory,username):
		self.directory = directory
		self.username = username
	@classmethod
	def new_meta(cls):
		return {
			'public_key':None,
			'private_key':None,
			'files':{},#filename:{owner,created,modified}
			'checkouts':[]#[{user,expiration}]
		}
	def full_filename(self,*fn):
		return os.path.join(self.directory,*fn)
	def get_meta_name(self):
		return self.full_filename(".meta")
	def open_file(self,fn,mode='r'):
		# returns a file handle to the file fn
		# within the "virtual filesystem"
		# as long as the username has the ability
		# to use the given permissions in mode.
		with open(self.get_meta_name()) as f:
			meta = json.load(f)
			if self.has_permission(meta,fn,mode):
				return open(self.full_filename(fn),mode)
		return None
	def has_permission(self,meta,filename,mode):
		return True
	# default checkout time is an hour.
	def checkout_file(self,filename,duration=86400):
		with open(self.get_meta_name(),'r+') as f:
			meta = json.load(f)
			if self.has_permission(filename,'w'):
				meta['files'][filename]['checked_out'] = self.username
				meta['files'][filename]['due_date'] = time.time() + duration
			json.dump(f,meta)
	def create_file(self,filename):
		with open(self.get_meta_name(),'r+'):
			meta = json.load(f)
			if not filename in meta['files']: