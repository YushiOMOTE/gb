import numpy as np
from functools import reduce

import alu


def _carry(b, *args):
	m = (1 << b) - 1
	s = reduce(lambda s, x: s + (x & m), args, 0)
	return s > m


def _borrow(n, *args):
	m = (1 << n) - 1
	a = args[0] & m
	s = reduce(lambda s, x: s + (x & m), args[1:], 0)
	return a < s


def _add(b, p, q, c=0):
	m = (1 << b) - 1
	s = (p + q + c) & m
	cs = [_carry(i * 4, p, q, c) for i in range(1, 5)]
	z = (s == 0)
	return (s, cs, z)


def _sub(b, p, q, c=0):
	m = (1 << b) - 1
	s = (p - q - c) & m
	cs = [_borrow(i * 4, p, q, c) for i in range(1, 5)]
	z = (s == 0)
	return (s, cs, z)


def add8(p, q, c=0):
	s, [h, c, _, _], z = _add(8, p, q, c)
	return s, [h, c], z


def add16(p, q, c=0):
	s, [_, _, h, c], z = _add(16, p, q, c)
	return s, [h, c], z


def sub8(p, q, c=0):
	s, [h, c, _, _], z = _sub(8, p, q, c)
	return s, [h, c], z


def add16e(p, q, c=0):
	s, [h, c, _, _], z = _add(16, p, np.uint16(np.int8(q)))
	return s, [h, c], z


import unittest


class AluTest(unittest.TestCase):
	def test_add8(self):
		v = add8(0x01, 0x02)
		self.assertEqual(v, (0x03, [False, False], False))
		v = add8(0x01, 0x0f)
		self.assertEqual(v, (0x10, [True, False], False))
		v = add8(0x19, 0x02)
		self.assertEqual(v, (0x1b, [False, False], False))
		v = add8(0xfa, 0x10)
		self.assertEqual(v, (0x0a, [False, True], False))
		v = add8(0xfa, 0x0a)
		self.assertEqual(v, (0x04, [True, True], False))
		v = add8(0x00, 0x00)
		self.assertEqual(v, (0x00, [False, False], True))
		v = add8(0xe0, 0x20)
		self.assertEqual(v, (0x00, [False, True], True))
		v = add8(0xed, 0x13)
		self.assertEqual(v, (0x00, [True, True], True))

	def test_add16(self):
		v = add16(0x1221, 0x3344)
		self.assertEqual(v, (0x4565, [False, False], False))
		v = add16(0x3fff, 0x0001)
		self.assertEqual(v, (0x4000, [True, False], False))
		v = add16(0xfa33, 0x1000)
		self.assertEqual(v, (0x0a33, [False, True], False))
		v = add16(0xe833, 0x2812)
		self.assertEqual(v, (0x1045, [True, True], False))
		v = add16(0x0000, 0x0000)
		self.assertEqual(v, (0x0000, [False, False], True))
		v = add16(0xe000, 0x2000)
		self.assertEqual(v, (0x0000, [False, True], True))
		v = add16(0xff00, 0x0100)
		self.assertEqual(v, (0x0000, [True, True], True))

	def test_sub8(self):
		v = sub8(0x0c, 0x01)
		self.assertEqual(v, (0x0b, [False, False], False))
		v = sub8(0x11, 0x02)
		self.assertEqual(v, (0x0f, [True, False], False))
		v = sub8(0x30, 0x40)
		self.assertEqual(v, (0xf0, [False, True], False))
		v = sub8(0xb1, 0xb2)
		self.assertEqual(v, (0xff, [True, True], False))
		v = sub8(0x1c, 0x1c)
		self.assertEqual(v, (0x00, [False, False], True))

	def test_16e(self):
		v = add16e(0x1201, 0x02)
		self.assertEqual(v, (0x1203, [False, False], False))
		v = add16e(0xff01, 0x0f)
		self.assertEqual(v, (0xff10, [True, False], False))
		v = add16e(0x3919, 0x02)
		self.assertEqual(v, (0x391b, [False, False], False))
		v = add16e(0xabfa, 0x10)
		self.assertEqual(v, (0xac0a, [False, True], False))
		v = add16e(0x11fa, 0x0a)
		self.assertEqual(v, (0x1204, [True, True], False))
		v = add16e(0x0000, 0x00)
		self.assertEqual(v, (0x0000, [False, False], True))
		v = add16e(0xffe0, 0x20)
		self.assertEqual(v, (0x0000, [False, True], True))
		v = add16e(0xffed, 0x13)
		self.assertEqual(v, (0x0000, [True, True], True))

		v = add16e(0xffed, 0xff)
		self.assertEqual(v, (0xffec, [True, True], False))


if __name__ == '__main__':
	unittest.main()
