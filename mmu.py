def load(f):
	with open(f, 'rb') as f:
		return f.read()


class MemCtrl(object):
	def __init__(self, debugger=None):
		self.ram = bytearray([0] * 0x10000)
		boot = load('boot.bin')
		self.ram[0:len(boot)] = bytearray(boot)
		self.ram[0x0104:48] = bytearray(boot)[0x00a8:]
		self.rdhooks = {}
		self.wrhooks = {}
		self.debugger = debugger

	def add_hook(self, hooks, addr, handler):
		if isinstance(addr, tuple):
			for a in range(addr[0], addr[1]):
				hooks[a] = handler
		else:
			hooks[addr] = handler

	def add_rdhook(self, addr, handler):
		self.add_hook(self.rdhooks, addr, handler)

	def add_wrhook(self, addr, handler):
		self.add_hook(self.wrhooks, addr, handler)

	def __getitem__(self, addr):
		if self.debugger:
			self.debugger.on_read(addr, self.ram[addr])

		if addr in self.rdhooks:
			val = self.rdhooks[addr](addr)
			if val:
				return val

		return self.ram[addr]

	def __setitem__(self, addr, val):
		if self.debugger:
			self.debugger.on_write(addr, val)

		if addr in self.wrhooks:
			if self.wrhooks[addr](addr, val):
				return

		self.ram[addr] = val & 0xff


class MemAccessor(object):
	def __init__(self, mc, unit):
		self.mc = mc
		self.unit = unit

	def __getitem__(self, addr):
		v = 0
		for i in range(0, self.unit):
			v |= (self.mc[addr + i] << (i * 8))
		return v

	def __setitem__(self, addr, val):
		for i in range(0, self.unit):
			self.mc[addr + i] = (val >> (i * 8)) & 0xff


class MemFetcher(object):
	def __init__(self, mc, debugger=None):
		self.mc = mc
		self.as8 = MemAccessor(mc, 1)
		self.as16 = MemAccessor(mc, 2)
		self.index = 0
		self.debugger = debugger

	def __getitem__(self, addr):
		return self.mc[addr]

	def __setitem__(self, addr, val):
		self.mc[addr] = val & 0xff

	def fetch_set(self, b):
		self.index = b

	def fetch(self):
		b = self.mc[self.index]

		if self.debugger:
			self.debugger.on_fetch(self, self.index, b)

		self.index += 1
		return b

	def fetch16(self):
		a = self.fetch()
		return (self.fetch() << 8) | a
