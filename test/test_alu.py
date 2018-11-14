import alu

import unittest


class AluTest(unittest.TestCase):
	def test_add8(self):
		v = alu.add8(0x01, 0x02)
		self.assertEqual(v, (0x03, False, False, False))
		v = alu.add8(0x01, 0x0f)
		self.assertEqual(v, (0x10, True, False, False))
		v = alu.add8(0x19, 0x02)
		self.assertEqual(v, (0x1b, False, False, False))
		v = alu.add8(0xfa, 0x10)
		self.assertEqual(v, (0x0a, False, True, False))
		v = alu.add8(0xfa, 0x0a)
		self.assertEqual(v, (0x04, True, True, False))
		v = alu.add8(0x00, 0x00)
		self.assertEqual(v, (0x00, False, False, True))
		v = alu.add8(0xe0, 0x20)
		self.assertEqual(v, (0x00, False, True, True))
		v = alu.add8(0xed, 0x13)
		self.assertEqual(v, (0x00, True, True, True))

	def test_add16(self):
		v = alu.add16(0x1221, 0x3344)
		self.assertEqual(v, (0x4565, False, False, False))
		v = alu.add16(0x3fff, 0x0001)
		self.assertEqual(v, (0x4000, True, False, False))
		v = alu.add16(0xfa33, 0x1000)
		self.assertEqual(v, (0x0a33, False, True, False))
		v = alu.add16(0xe833, 0x2812)
		self.assertEqual(v, (0x1045, True, True, False))
		v = alu.add16(0x0000, 0x0000)
		self.assertEqual(v, (0x0000, False, False, True))
		v = alu.add16(0xe000, 0x2000)
		self.assertEqual(v, (0x0000, False, True, True))
		v = alu.add16(0xff00, 0x0100)
		self.assertEqual(v, (0x0000, True, True, True))

	def test_sub8(self):
		v = alu.sub8(0x0c, 0x01)
		self.assertEqual(v, (0x0b, False, False, False))
		v = alu.sub8(0x11, 0x02)
		self.assertEqual(v, (0x0f, True, False, False))
		v = alu.sub8(0x30, 0x40)
		self.assertEqual(v, (0xf0, False, True, False))
		v = alu.sub8(0xb1, 0xb2)
		self.assertEqual(v, (0xff, True, True, False))
		v = alu.sub8(0x1c, 0x1c)
		self.assertEqual(v, (0x00, False, False, True))

	def test_16e(self):
		v = alu.add16e(0x1201, 0x02)
		self.assertEqual(v, (0x1203, False, False, False))
		v = alu.add16e(0xff01, 0x0f)
		self.assertEqual(v, (0xff10, True, False, False))
		v = alu.add16e(0x3919, 0x02)
		self.assertEqual(v, (0x391b, False, False, False))
		v = alu.add16e(0xabfa, 0x10)
		self.assertEqual(v, (0xac0a, False, True, False))
		v = alu.add16e(0x11fa, 0x0a)
		self.assertEqual(v, (0x1204, True, True, False))
		v = alu.add16e(0x0000, 0x00)
		self.assertEqual(v, (0x0000, False, False, True))
		v = alu.add16e(0xffe0, 0x20)
		self.assertEqual(v, (0x0000, False, True, True))
		v = alu.add16e(0xffed, 0x13)
		self.assertEqual(v, (0x0000, True, True, True))

		v = alu.add16e(0xffed, 0xff)
		self.assertEqual(v, (0xffec, True, True, False))


if __name__ == '__main__':
	unittest.main()
