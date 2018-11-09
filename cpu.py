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


class MemCtrl(object):
	def __init__(self):
		self.ram = np.fromfile('sgb_bios.bin', dtype=np.uint8)
		self.as8 = MemAccessor(self, 1)
		self.as16 = MemAccessor(self, 2)

	def __getitem__(self, addr):
		return self.ram[addr]

	def __setitem__(self, addr, val):
		self.ram[addr] = np.uint8(val)


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
		self.mc = mc

	def fetch(self):
		b = self.mc[self.regs.pc]
		print('fetch {:04x} {:02x}'.format(self.regs.pc, b))
		self.regs.pc += 1
		return b

	def fetch16(self):
		a = self.fetch()
		return (self.fetch() << 8) | a

	def decode(self):
		b = self.fetch()
		if b == 0xcb:
			b = self.fetch()
			inst.op(self, b << 8 | b)
		else:
			inst.op(self, b)

import unittest


class TestCpu(unittest.TestCase):
	def _test_ld(self, op, t, f):
		if not isinstance(op, list):
			op = [op]
		m = op + [i % 254 + 1 for i in range(65536)]
		cpu = Cpu(m)
		cpu.regs.a = 1
		cpu.regs.b = 2
		cpu.regs.c = 3
		cpu.regs.d = 4
		cpu.regs.e = 5
		cpu.regs.h = 6
		cpu.regs.l = 7

		op = [f'{i:02x}' for i in op]

		if t != f:
			x = self._get(cpu.regs, m, t)
			y = self._get(cpu.regs, m, f)
			print(f'{op}: {x:02x} != {y:02x}')
			self.assertNotEqual(x, y)

		y = self._get(cpu.regs, m, f)
		cpu.decode()
		x = self._get(cpu.regs, m, t)

		print(f'{op}: ld {t}, {f}: {x:02x} == {y:02x}')
		self.assertEqual(x, y)

		return cpu

	def _get(self, r, m, s):
		if isinstance(s, int):
			return s
		elif s.startswith('('):
			s = s[1:-1]
			return m[self._eval(r, m, s)]
		else:
			return self._eval(r, m, s)

	def _eval(self, r, m, s):
		v = 0
		for i in s.split('+'):
			try:
				v += int(i, 0)
			except:
				v += getattr(r, i)
		return v

	#  LD B,n 06 8
	#  LD C,n 0E 8
	#  LD D,n 16 8
	#  LD E,n 1E 8
	#  LD H,n 26 8
	#  LD L,n 2E 8

	def test_06(self):
		self._test_ld([0x06, 0xfb], 'b', 0xfb)

	def test_0e(self):
		self._test_ld([0x0e, 0xfb], 'c', 0xfb)

	def test_16(self):
		self._test_ld([0x16, 0xfb], 'd', 0xfb)

	def test_1e(self):
		self._test_ld([0x1e, 0xfb], 'e', 0xfb)

	def test_26(self):
		self._test_ld([0x26, 0xfb], 'h', 0xfb)

	def test_2e(self):
		self._test_ld([0x2e, 0xfb], 'l', 0xfb)

	# LD A,A 7F 4
	# LD A,B 78 4
	# LD A,C 79 4
	# LD A,D 7A 4
	# LD A,E 7B 4
	# LD A,H 7C 4
	# LD A,L 7D 4
	# LD A,(HL) 7E 8

	def test_7f(self):
		self._test_ld(0x7f, 'a', 'a')

	def test_78(self):
		self._test_ld(0x78, 'a', 'b')

	def test_79(self):
		self._test_ld(0x79, 'a', 'c')

	def test_7a(self):
		self._test_ld(0x7a, 'a', 'd')

	def test_7b(self):
		self._test_ld(0x7b, 'a', 'e')

	def test_7c(self):
		self._test_ld(0x7c, 'a', 'h')

	def test_7d(self):
		self._test_ld(0x7d, 'a', 'l')

	def test_7e(self):
		self._test_ld(0x7e, 'a', '(hl)')

	# LD B,B 40 4
	# LD B,C 41 4
	# LD B,D 42 4
	# LD B,E 43 4
	# LD B,H 44 4
	# LD B,L 45 4
	# LD B,(HL) 46 8

	def test_40(self):
		self._test_ld(0x40, 'b', 'b')

	def test_41(self):
		self._test_ld(0x41, 'b', 'c')

	def test_42(self):
		self._test_ld(0x42, 'b', 'd')

	def test_43(self):
		self._test_ld(0x43, 'b', 'e')

	def test_44(self):
		self._test_ld(0x44, 'b', 'h')

	def test_45(self):
		self._test_ld(0x45, 'b', 'l')

	def test_46(self):
		self._test_ld(0x46, 'b', '(hl)')

	# LD C,B 48 4
	# LD C,C 49 4
	# LD C,D 4A 4
	# LD C,E 4B 4
	# LD C,H 4C 4
	# LD C,L 4D 4
	# LD C,(HL) 4E 8

	def test_48(self):
		self._test_ld(0x48, 'c', 'b')

	def test_49(self):
		self._test_ld(0x49, 'c', 'c')

	def test_4a(self):
		self._test_ld(0x4a, 'c', 'd')

	def test_4b(self):
		self._test_ld(0x4b, 'c', 'e')

	def test_4c(self):
		self._test_ld(0x4c, 'c', 'h')

	def test_4d(self):
		self._test_ld(0x4d, 'c', 'l')

	def test_4e(self):
		self._test_ld(0x4e, 'c', '(hl)')

	# LD D,B 50 4
	# LD D,C 51 4
	# LD D,D 52 4
	# LD D,E 53 4
	# LD D,H 54 4
	# LD D,L 55 4
	# LD D,(HL) 56 8

	def test_50(self):
		self._test_ld(0x50, 'd', 'b')

	def test_51(self):
		self._test_ld(0x51, 'd', 'c')

	def test_52(self):
		self._test_ld(0x52, 'd', 'd')

	def test_53(self):
		self._test_ld(0x53, 'd', 'e')

	def test_54(self):
		self._test_ld(0x54, 'd', 'h')

	def test_55(self):
		self._test_ld(0x55, 'd', 'l')

	def test_56(self):
		self._test_ld(0x56, 'd', '(hl)')

	# LD E,B 58 4
	# LD E,C 59 4
	# LD E,D 5A 4
	# LD E,E 5B 4
	# LD E,H 5C 4
	# LD E,L 5D 4
	# LD E,(HL) 5E 8

	def test_58(self):
		self._test_ld(0x58, 'e', 'b')

	def test_59(self):
		self._test_ld(0x59, 'e', 'c')

	def test_5a(self):
		self._test_ld(0x5a, 'e', 'd')

	def test_5b(self):
		self._test_ld(0x5b, 'e', 'e')

	def test_5c(self):
		self._test_ld(0x5c, 'e', 'h')

	def test_5d(self):
		self._test_ld(0x5d, 'e', 'l')

	def test_5e(self):
		self._test_ld(0x5e, 'e', '(hl)')

	# LD H,B 60 4
	# LD H,C 61 4
	# LD H,D 62 4
	# LD H,E 63 4
	# LD H,H 64 4
	# LD H,L 65 4
	# LD H,(HL) 66 8

	def test_60(self):
		self._test_ld(0x60, 'h', 'b')

	def test_61(self):
		self._test_ld(0x61, 'h', 'c')

	def test_62(self):
		self._test_ld(0x62, 'h', 'd')

	def test_63(self):
		self._test_ld(0x63, 'h', 'e')

	def test_64(self):
		self._test_ld(0x64, 'h', 'h')

	def test_65(self):
		self._test_ld(0x65, 'h', 'l')

	def test_66(self):
		self._test_ld(0x66, 'h', '(hl)')

	# LD L,B 68 4
	# LD L,C 69 4
	# LD L,D 6A 4
	# LD L,E 6B 4
	# LD L,H 6C 4
	# LD L,L 6D 4
	# LD L,(HL) 6E 8

	def test_68(self):
		self._test_ld(0x68, 'l', 'b')

	def test_69(self):
		self._test_ld(0x69, 'l', 'c')

	def test_6a(self):
		self._test_ld(0x6a, 'l', 'd')

	def test_6b(self):
		self._test_ld(0x6b, 'l', 'e')

	def test_6c(self):
		self._test_ld(0x6c, 'l', 'h')

	def test_6d(self):
		self._test_ld(0x6d, 'l', 'l')

	def test_6e(self):
		self._test_ld(0x6e, 'l', '(hl)')

	# LD (HL),B 70 8
	# LD (HL),C 71 8
	# LD (HL),D 72 8
	# LD (HL),E 73 8
	# LD (HL),H 74 8
	# LD (HL),L 75 8
	# LD (HL),n 36 12

	def test_70(self):
		self._test_ld(0x70, '(hl)', 'b')

	def test_71(self):
		self._test_ld(0x71, '(hl)', 'c')

	def test_72(self):
		self._test_ld(0x72, '(hl)', 'd')

	def test_73(self):
		self._test_ld(0x73, '(hl)', 'e')

	def test_74(self):
		self._test_ld(0x74, '(hl)', 'h')

	def test_75(self):
		self._test_ld(0x75, '(hl)', 'l')

	def test_36(self):
		self._test_ld([0x36, 0x42], '(hl)', 0x42)

	# LD A,B 78 4
	# LD A,C 79 4
	# LD A,D 7A 4
	# LD A,E 7B 4
	# LD A,H 7C 4
	# LD A,L 7D 4

	def test_78(self):
		self._test_ld(0x78, 'a', 'b')

	def test_79(self):
		self._test_ld(0x79, 'a', 'c')

	def test_7a(self):
		self._test_ld(0x7a, 'a', 'd')

	def test_7b(self):
		self._test_ld(0x7b, 'a', 'e')

	def test_7c(self):
		self._test_ld(0x7c, 'a', 'h')

	def test_7d(self):
		self._test_ld(0x7d, 'a', 'l')

	# LD A,(BC) 0A 8
	# LD A,(DE) 1A 8
	# LD A,(HL) 7E 8
	# LD A,(nn) FA 16
	# LD A,# 3E 8

	def test_0a(self):
		self._test_ld(0x0a, 'a', '(bc)')

	def test_1a(self):
		self._test_ld(0x1a, 'a', '(de)')

	def test_fa(self):
		self._test_ld([0xfa, 0x39, 0x47], 'a', '(0x4739)')

	def test_3e(self):
		self._test_ld([0x3e, 0xdd], 'a', 0xdd)

	# LD B,A 47 4
	# LD C,A 4F 4
	# LD D,A 57 4
	# LD E,A 5F 4
	# LD H,A 67 4
	# LD L,A 6F 4

	def test_47(self):
		self._test_ld(0x47, 'b', 'a')

	def test_4f(self):
		self._test_ld(0x4f, 'c', 'a')

	def test_57(self):
		self._test_ld(0x57, 'd', 'a')

	def test_5f(self):
		self._test_ld(0x5f, 'e', 'a')

	def test_67(self):
		self._test_ld(0x67, 'h', 'a')

	def test_6f(self):
		self._test_ld(0x6f, 'l', 'a')

	# LD (BC),A 02 8
	# LD (DE),A 12 8
	# LD (HL),A 77 8
	# LD (nn),A EA 16

	def test_02(self):
		self._test_ld(0x02, '(bc)', 'a')

	def test_12(self):
		self._test_ld(0x12, '(de)', 'a')

	def test_77(self):
		self._test_ld(0x77, '(hl)', 'a')

	def test_ea(self):
		self._test_ld([0xea, 0x34, 0x12], '(0x1234)', 'a')

	# LD A,(C) F2 8

	def test_f2(self):
		self._test_ld(0xf2, 'a', '(0xff00+c)')

	# LD ($FF00+C),A E2 8

	def test_e2(self):
		self._test_ld(0xe2, '(0xff00+c)', 'a')

	# LDD A,(HL) 3A 8

	def test_3a(self):
		cpu = self._test_ld(0x3a, 'a', '(hl)')
		self.assertEqual(cpu.regs.h, 6)
		self.assertEqual(cpu.regs.l, 6)

	# LDD (HL),A 32 8

	def test_32(self):
		# hl+1 because hl is decreased by this instruction
		cpu = self._test_ld(0x32, '(hl+1)', 'a')
		self.assertEqual(cpu.regs.h, 6)
		self.assertEqual(cpu.regs.l, 6)

	# LDI A,(HL) 2A 8

	def test_2a(self):
		cpu = self._test_ld(0x2a, 'a', '(hl)')
		self.assertEqual(cpu.regs.h, 6)
		self.assertEqual(cpu.regs.l, 8)

	# LDI (HL),A 22 8

	def test_22(self):
		# hl+-1 because hl is increased by this instruction
		cpu = self._test_ld(0x22, '(hl+-1)', 'a')
		self.assertEqual(cpu.regs.h, 6)
		self.assertEqual(cpu.regs.l, 8)

	# LD ($FF00+n),A E0 12

	def test_e0(self):
		self._test_ld([0xe0, 0x55], '(0xff00+0x55)', 'a')

	# LD A,($FF00+n) F0 12

	def test_f0(self):
		self._test_ld([0xf0, 0x55], 'a', '(0xff00+0x55)')

	# LD BC,nn 01 12
	# LD DE,nn 11 12
	# LD HL,nn 21 12
	# LD SP,nn 31 12

	def test_01(self):
		self._test_ld([0x01, 0x39, 0x55], 'bc', 0x5539)

	def test_11(self):
		self._test_ld([0x11, 0x39, 0x55], 'de', 0x5539)

	def test_21(self):
		self._test_ld([0x21, 0x39, 0x55], 'hl', 0x5539)

	def test_31(self):
		self._test_ld([0x31, 0x39, 0x55], 'sp', 0x5539)

	# LD SP,HL F9 8

	def test_f9(self):
		self._test_ld(0xf9, 'sp', 'hl')

	def test_f8(self):
		self._test_ld([0xf8, 0x33], 'hl', 'sp+0x33')

	def test_08(self):
		self._test_ld([0x08, 0x33, 0x44], '(0x4433)', 'sp')

	def _pushpop(self, op):
		m = op + [i % 254 + 1 for i in range(65536)]
		cpu = Cpu(m)

		cpu.regs.sp = 0x1004
		m[0x1004] = 0x01
		m[0x1005] = 0x02
		m[0x1006] = 0x03
		m[0x1007] = 0x04

		return cpu

	# PUSH AF F5 16
	# PUSH BC C5 16
	# PUSH DE D5 16
	# PUSH HL E5 16
	# POP AF F1 12
	# POP BC C1 12
	# POP DE D1 12
	# POP HL E1 12

	def test_pushpop(self):
		cpu = self._pushpop([0xf5, 0xc5, 0xd5, 0xe5,
							 0xf1, 0xc1, 0xd1, 0xe1,
							 0xe1, 0xd1])
		cpu.regs.af = 0x1122
		cpu.regs.bc = 0x2233
		cpu.regs.de = 0x4455
		cpu.regs.hl = 0x6677

		self.assertEqual(cpu.regs.af, 0x1122)
		self.assertEqual(cpu.regs.bc, 0x2233)
		self.assertEqual(cpu.regs.de, 0x4455)
		self.assertEqual(cpu.regs.hl, 0x6677)

		cpu.decode()
		self.assertEqual(cpu.mc[0x1002], 0x22)
		self.assertEqual(cpu.mc[0x1003], 0x11)
		cpu.decode()
		self.assertEqual(cpu.mc[0x1000], 0x33)
		self.assertEqual(cpu.mc[0x1001], 0x22)
		cpu.decode()
		self.assertEqual(cpu.mc[0x0ffe], 0x55)
		self.assertEqual(cpu.mc[0x0fff], 0x44)
		cpu.decode()
		self.assertEqual(cpu.mc[0x0ffc], 0x77)
		self.assertEqual(cpu.mc[0x0ffd], 0x66)

		cpu.decode()
		self.assertEqual(cpu.regs.af, 0x6677)
		cpu.decode()
		self.assertEqual(cpu.regs.bc, 0x4455)
		cpu.decode()
		self.assertEqual(cpu.regs.de, 0x2233)
		cpu.decode()
		self.assertEqual(cpu.regs.hl, 0x1122)

		cpu.decode()
		cpu.decode()
		self.assertEqual(cpu.regs.de, 0x0403)
		self.assertEqual(cpu.regs.hl, 0x0201)

if __name__ == '__main__':
	unittest.main()

	# * read as16 or as8
	# * read flags
