import ui
from scene import *


def light(c):
	return f'{c:06x}'


def shadow(c):
	r = max((c >> 16) & 0xff - 0x35, 0x00)
	g = max((c >> 8) & 0xff - 0x35, 0x00)
	b = max((c >> 0) & 0xff - 0x35, 0x00)
	return f'{r:02x}{g:02x}{b:02x}'


class Lcd(Scene):
	def __init__(self):
		super().__init__()
		self.width = 160
		self.height = 144
		self.map = [0xd9d9d9] * self.width * self.height

	def setup(self):
		self.background_color = 'white'

	def draw(self):
		sw, sh = ui.get_screen_size()
		s = 2
		xoff = (sw - self.width * s) / 2
		yoff = 30

		for x in range(self.width):
			for y in range(self.height):
				i = x + y * self.width
				c = self.map[i]
				px = int(x * s + xoff)
				py = int(sh - y * s - yoff)
				fill(shadow(c))
				rect(px, py, s, s)
				fill(light(c))
				rect(px, py, s - 1, s - 1)

	def show(self):
		run(self, orientation=PORTRAIT)


class Gpu:
	def __init__(self, hide=False):
		super().__init__()
		self.lcd = Lcd()

		if not hide:
			self.lcd.show()

	def on_read(self, addr):
		#print(f'gpu read: {addr:04x}')
		pass

	def on_write(self, addr, val):
		#print(f'gpu write: {addr:04x}, {val:04x}')
		pass
