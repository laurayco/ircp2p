
class Keychain:
	def __init__(self):
		self.networks = {}
	def install_network(self,network,public_key,private_key,friends):
		self.networks[network] = {
			'public_key':public_key,
			'private_key':private_key,
			'friends':friends
		}
	def public_key(self,network):
		return self.networks[network]['public_key']