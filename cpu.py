import inst


class Flags(object):
	def __init__(self, *args, **kwargs):
		self.val = 0

	@property
	def z(self) -> int:
		return (self.val >> 7) & 1

	@z.setter
	def z(self, v):
		b = 0x80 if v else 0
		self.val = (self.val & 0x7f) | b

	@property
	def n(self) -> int:
		return (self.val >> 6) & 1

	@n.setter
	def n(self, v):
		b = 0x40 if v else 0
		self.val = (self.val & 0xbf) | b

	@property
	def h(self) -> int:
		return (self.val >> 5) & 1

	@h.setter
	def h(self, v):
		b = 0x20 if v else 0
		self.val = (self.val & 0xdf) | b

	@property
	def c(self) -> int:
		return (self.val >> 4) & 1

	@c.setter
	def c(self, v):
		b = 0x10 if v else 0
		self.val = (self.val & 0xef) | b

	def __str__(self):
		return '{}{}{}{}____'.format('z' if self.z else '_', 'n' if self.n else '_',
		                             'h' if self.h else '_', 'c' if self.c else '_')


class Regs(object):
	def __init__(self):
		self.a = 0
		self.f = Flags()
		self.b = 0
		self.c = 0
		self.d = 0
		self.e = 0
		self.h = 0
		self.l = 0
		self.sp = 0
		self.pc = 0

	@property
	def af(self):
		return self.a << 8 | self.f.val

	@af.setter
	def af(self, v):
		self.a = (v >> 8) & 0xff
		self.f.val = v & 0xff

	@property
	def bc(self):
		return self.b << 8 | self.c

	@bc.setter
	def bc(self, v):
		self.b = (v >> 8) & 0xff
		self.c = v & 0xff

	@property
	def de(self):
		return self.d << 8 | self.e

	@de.setter
	def de(self, v):
		self.d = (v >> 8) & 0xff
		self.e = v & 0xff

	@property
	def hl(self):
		return self.h << 8 | self.l

	@hl.setter
	def hl(self, v):
		self.h = (v >> 8) & 0xff
		self.l = v & 0xff

	def __str__(self):
		s = '''
regs:
	  a [{:02x}], f [{:02x}]
	  b [{:02x}], c [{:02x}]
	  d [{:02x}], e [{:02x}]
	  h [{:02x}], l [{:02x}]
	 sp [{:04x}]
	 pc [{:04x}]
	flg [{}]
		'''.format(self.a, self.f.val, self.b, self.c, self.d, self.e, self.h,
		           self.l, self.sp, self.pc, str(self.f))
		return s


def load(f):
	with open(f, 'rb') as f:
		return f.read()


class MemCtrl(object):
	def __init__(self):
		self.ram = [0] * 0x10000
		boot = load('boot.bin')
		self.ram[0:len(boot)] = boot
		self.hooks = {}

	def add_hook(self, low, high, read, write):
		for i in range(low, high + 1):
			self.hooks[i] = (read, write)

	def __getitem__(self, addr):
		if addr in self.hooks:
			val = self.hooks[addr][0](addr)
			if val:
				return val

		return self.ram[addr]

	def __setitem__(self, addr, val):
		if addr in self.hooks:
			if self.hooks[addr][1](addr, val):
				return val

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


class Cpu(object):
	def __init__(self, mc, debugger=None):
		self.regs = Regs()
		self.mc = MemFetcher(mc, debugger=debugger)
		self.ei = False
		self.di = False
		self.intr = False
		self.halt = False
		self.stop = False
		self.time = 0
		self.debugger = debugger

	def decode(self):
		self.mc.fetch_set(self.regs.pc)

		b = self.mc.fetch()
		if b == 0xcb:
			b = b << 8 | self.mc.fetch()
		inst.op(self, b, debugger=self.debugger)

	def push(self, v):
		self.mc[self.regs.sp - 1] = (v >> 8) & 0xff
		self.mc[self.regs.sp - 2] = v & 0xff
		self.regs.sp -= 2

	def pop(self):
		v = self.mc[self.regs.sp] & 0xff
		v |= (self.mc[self.regs.sp + 1] << 8) & 0xff00
		self.regs.sp += 2
		return v

	def run(self):
		if self.debugger:
			self.debugger.on_start(self)

		while True:
			if self.intr:
				# TODO: interrupt
				pass

			if self.ei:
				self.ei = False
				self.intr = True
			if self.di:
				self.di = False
				self.intr = False

			if self.debugger:
				self.debugger.before_exec()

			self.decode()

			if self.debugger:
				self.debugger.after_exec()
