import numpy as np
import inst


class Flags(object):
	def __init__(self, *args, **kwargs):
		self._v = np.uint8()

	@property
	def z(self) -> int:
		return int(bool(self._v & 0x80))

	@z.setter
	def z(self, v):
		b = int(bool(v))
		self.val = (self.val & 0x7f) | (b << 7)

	@property
	def n(self) -> int:
		return int(bool(self._v & 0x40))

	@n.setter
	def n(self, v):
		b = int(bool(v))
		self.val = (self.val & 0xbf) | (b << 6)

	@property
	def h(self) -> int:
		return int(bool(self._v & 0x20))

	@h.setter
	def h(self, v):
		b = int(bool(v))
		self.val = (self.val & 0xdf) | (b << 5)

	@property
	def c(self) -> int:
		return int(bool(self._v & 0x10))

	@c.setter
	def c(self, v):
		b = int(bool(v))
		self.val = (self.val & 0xef) | (b << 4)

	@property
	def val(self) -> np.uint8:
		return self._v

	@val.setter
	def val(self, v):
		self._v = np.uint8(v)

	def __str__(self):
		return '{}{}{}{}____'.format(
		    'z' if self.z() else '_', 'n' if self.n() else '_',
		    'h' if self.h() else '_', 'c' if self.c() else '_')


class Regs(object):
	def __init__(self):
		self._a = np.uint8()
		self._f = Flags()
		self._b = np.uint8()
		self._c = np.uint8()
		self._d = np.uint8()
		self._e = np.uint8()
		self._h = np.uint8()
		self._l = np.uint8()
		self._sp = np.uint16()
		self._pc = np.uint16()

	@property
	def a(self) -> np.uint8:
		return self._a

	@a.setter
	def a(self, v):
		self._a = np.uint8(v)

	@property
	def af(self):
		return np.uint16(self.a << 8 | self.f.val)

	@af.setter
	def af(self, v):
		self.a = (v >> 8) & 0xff
		self.f.val = v & 0xff

	@property
	def b(self) -> np.uint8:
		return self._b

	@b.setter
	def b(self, v):
		self._b = np.uint8(v)

	@property
	def c(self) -> np.uint8:
		return self._c

	@c.setter
	def c(self, v):
		self._c = np.uint8(v)

	@property
	def bc(self):
		return np.uint16(self.b << 8 | self.c)

	@bc.setter
	def bc(self, v):
		self.b = (v >> 8) & 0xff
		self.c = v & 0xff

	@property
	def d(self) -> np.uint8:
		return self._d

	@d.setter
	def d(self, v):
		self._d = np.uint8(v)

	@property
	def e(self) -> np.uint8:
		return self._e

	@e.setter
	def e(self, v):
		self._e = np.uint8(v)

	@property
	def de(self):
		return np.uint16(self.d << 8 | self.e)

	@de.setter
	def de(self, v):
		self.d = (v >> 8) & 0xff
		self.e = v & 0xff

	@property
	def h(self) -> np.uint8:
		return self._h

	@h.setter
	def h(self, v):
		self._h = np.uint8(v)

	@property
	def l(self) -> np.uint8:
		return self._l

	@l.setter
	def l(self, v):
		self._l = np.uint8(v)

	@property
	def hl(self):
		return np.uint16(self.h << 8 | self.l)

	@hl.setter
	def hl(self, v):
		self.h = (v >> 8) & 0xff
		self.l = v & 0xff

	@property
	def sp(self) -> np.uint16:
		return self._sp

	@sp.setter
	def sp(self, v):
		self._sp = np.uint16(v)

	@property
	def pc(self) -> np.uint16:
		return self._pc

	@pc.setter
	def pc(self, v):
		self._pc = np.uint16(v)

	@property
	def f(self) -> Flags:
		return self._f

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
		'''.format(self._a, self._f.val, self._b, self._c, self._d, self._e, self._h,
		           self._l, self._sp, self._pc, str(self._f))
		return s


class MemCtrl(object):
	def __init__(self):
		self.ram = np.fromfile('sgb_bios.bin', dtype=np.uint8)

	def __getitem__(self, addr):
		return self.ram[addr]

	def __setitem__(self, addr, val):
		self.ram[addr] = np.uint8(val)


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
	def __init__(self, mc):
		self.mc = mc
		self.as8 = MemAccessor(mc, 1)
		self.as16 = MemAccessor(mc, 2)
		self.index = 0

	def __getitem__(self, addr):
		return self.mc[addr]

	def __setitem__(self, addr, val):
		self.mc[addr] = np.uint8(val)

	def fetch_set(self, b):
		self.index = b

	def fetch(self):
		b = self.mc[self.index]
		# print('fetch {:04x} {:02x}'.format(self.index, b))
		self.index += 1
		return b

	def fetch16(self):
		a = self.fetch()
		return (self.fetch() << 8) | a


class Op(object):
	def __init__(self, v):
		self.x = (v >> 6) & 3
		self.y = (v >> 3) & 7
		self.z = v & 7
		self.p = (v >> 4) & 3
		self.q = (v >> 3) & 1


class Cpu(object):
	def __init__(self, mc):
		self.regs = Regs()
		self.mc = MemFetcher(mc)
		self.ie = False
		self.id = False
		self.intr = False
		self.halt = False
		self.stop = False
		self.time = 0

	def decode(self):
		self.mc.fetch_set(self.regs.pc)

		b = self.mc.fetch()
		if b == 0xcb:
			b = self.mc.fetch()
			inst.op(self, b << 8 | b)
		else:
			inst.op(self, b)

	def push(self, v):
		self.mc[self.regs.sp - 1] = (v >> 8) & 0xff
		self.mc[self.regs.sp - 2] = v & 0xff
		self.regs.sp -= 2

	def pop(self):
		v = self.mc[self.regs.sp] & 0xff
		v |= (self.mc[self.regs.sp + 1] << 8) & 0xff00
		self.regs.sp += 2
		return v
