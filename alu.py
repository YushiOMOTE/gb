import numpy as np
from functools import reduce


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
