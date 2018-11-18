import ui
from scene import *


class Lcd(Scene):
	def __init__(self):
		super().__init__()
		self.width = 166
		self.height = 140
		self.vram = [0.3] * self.width * self.height

	def setup(self):
		self.background_color = 'white'

	def draw(self):
		#return
		sw, sh = self.size
		s = 2
		xoff = (sw - self.width * s) // 2
		yoff = 30  # sh - self.height * s - 30

		#image(self.imgid, xoff, yoff, self.width * s, self.height * s)
		#return

		w = self.width
		h = self.height
		vram = self.vram

		for x in range(w):
			for y in range(h):
				i = x + y * w
				px = x * s + xoff
				py = sh - y * s - yoff

				fill(vram[i])
				rect(px, py, s, s)

	def show(self):
		run(self, orientation=PORTRAIT, frame_interval=3)


class Gpu:
	def __init__(self, mc, debugger=None, show=True):
		super().__init__()
		self.lcd = Lcd()
		self.enable = False
		self.winbase = 0x9800
		self.winenable = False
		self.bgwinbase = 0x8800
		self.bgbase = 0x9800
		self.spsz = (8, 8)
		self.spenable = False
		self.bgenable = False
		self.mc = mc
		self.palette = [0.9, 0.7, 0.5, 0.3]
		self.buf = [0.3] * 256 * 256
		self.show = show
		self.mode = 2
		self.ly = 0
		self.clks = 0
		self.scx = 0
		self.scy = 0
		self.lyc = 0
		self.debugger = debugger

		mc.add_rdhook((0xff40, 0xff4f), self.on_read)
		mc.add_wrhook((0xff40, 0xff4f), self.on_write)
		mc.add_wrhook((0x8000, 0x9fff), self.on_oam_update)

	def setup(self, show=True):
		if self.debugger:
			self.debugger.on_start_gpu(self)
		if self.show:
			self.lcd.show()

	def on_read(self, addr):
		#print(f'gpu read: {addr:04x}')
		if addr == 0xff44:
			#print(f'line {self.line}')
			return self.ly
		elif addr == 0xff45:
			return self.lyc
		pass

	def on_write(self, addr, val):
		#print(f'gpu write: {addr:04x}, {val:04x}')
		if addr == 0xff40:
			self.write_ctrl(val)
		elif addr == 0xff42:
			self.scy = val
		elif addr == 0xff43:
			self.scx = val
		elif addr == 0xff44:
			self.ly = 0
		elif addr == 0xff45:
			self.lyc = val
		else:
			print(f'gpu write: {addr:04x}, {val:04x}')
		pass

	def on_oam_update(self, addr, val):
		pass

	def write_ctrl(self, v):
		old_enable = self.enable

		self.enable = v & 0x80
		if v & 0x40:
			self.winbase = 0x9c00
		else:
			self.winbase = 0x9800
		self.winenable = v & 0x20
		if v & 0x10:
			self.bgwinbase = 0x8000
		else:
			self.bgwinbase = 0x8800
		if v & 0x08:
			self.bgbase = 0x9c00
		else:
			self.bgbase = 0x9800
		if v & 0x04:
			self.spsz = (8, 8)
		else:
			self.spsz = (8, 16)
		self.spenable = v & 0x02
		self.bgenable = v & 0x01

		print(f'ctrl: {v:04x}')
		print(f'winbase: {self.winbase:04x}')
		print(f'bgbase: {self.bgbase:04x}')
		print(f'bgwinbase: {self.bgwinbase:04x}')

		if not old_enable and self.enable:
			print(f'LCD enabled')
			self.ly = 0
			self.clks = 0
			self.mode = 2
		elif old_enable and not self.enable:
			print(f'LCD disable')

	def step(self, t):
		if not self.enable:
			return

		self.clks += t

		if self.mode == 2:
			if self.clks >= 80:
				self.clks = 0
				self.mode = 3
		elif self.mode == 3:
			if self.clks >= 172:
				self.clks = 0
				self.mode = 0
				self.scanline()
		elif self.mode == 0:
			if self.clks >= 204:
				self.clks = 0
				self.ly += 1
				if self.ly == 143:
					self.mode = 1
				else:
					self.mode = 2
		elif self.mode == 1:
			if self.clks >= 456:
				self.clks = 0
				self.ly += 1
				if self.ly > 153:
					self.mode = 2
					self.ly = 0

	def scanline(self):
		if self.ly >= self.lcd.height:
			return

		self.fetchline()

		vram = self.lcd.vram
		y = self.ly
		yy = (y + self.scy) % 256
		for x in range(0, self.lcd.width):
			xx = (x + self.scx) % 256
			i = x + y * self.lcd.width
			j = xx + yy * 256
			vram[i] = self.buf[j]

	def fetchline(self):
		m = self.mc
		tmap = self.bgbase
		tset = self.bgwinbase
		y = (self.ly + self.scy) % 256

		ty = y // 8
		j = y % 8

		for tx in range(32):
			i = tx + ty * 32
			tile = tset + m[tmap + i] * 16

			l = m[tile + j * 2]
			h = m[tile + j * 2 + 1]

			for x in range(8):
				col = (l >> (7 - x)) & 1
				col |= ((h >> (7 - x)) & 1) << 1
				col = self.palette[col]
				xx = (i % 32) * 8 + x
				yy = (i // 32) * 8 + j
				self.buf[xx + yy * 256] = col
