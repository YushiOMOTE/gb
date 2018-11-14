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


def _add(b, p, q, c=0, hb=4, cb=8):
	m = (1 << b) - 1
	s = (p + q + c) & m
	h = _carry(hb, p, q, c)
	c = _carry(cb, p, q, c)
	z = (s == 0)
	return (s, h, c, z)


def _sub(b, p, q, c=0, hb=4, cb=8):
	m = (1 << b) - 1
	s = (p - q - c) & m
	h = _borrow(hb, p, q, c)
	c = _borrow(cb, p, q, c)
	z = (s == 0)
	return (s, h, c, z)


def signed(v):
	if v & 0x80:
		return 0xff00 | v
	else:
		return v


def add8(p, q, c=0):
	return _add(8, p, q, c)


def add16(p, q, c=0):
	return _add(16, p, q, c, 12, 16)


def sub8(p, q, c=0):
	return _sub(8, p, q, c)


def add16e(p, q, c=0):
	return _add(16, p, signed(q), c)
