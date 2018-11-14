from cpu import Cpu, MemCtrl
from debug import Debugger
import time
from gpu import Gpu
import sys


class PrintDebugger(Debugger):
	def __init__(self, verbose=False, perf=False):
		self.last = 0
		self.iters = 0
		self.verbose = verbose
		self.perf = perf
		self.cpu = None
		self.breaks = {}
		self.prompt = False
		self.step = False
		self.mnem = None

	def on_start(self, cpu):
		self.last = time.time()
		self.cpu = cpu

	def before_exec(self):
		if self.verbose:
			print(f'{str(self.cpu.regs)}')

	def after_exec(self):
		if not self.perf:
			return

		self.iters += 1
		if self.iters % 10000 == 0:
			t = time.time()
			print(f'{10000 / (t - self.last)} ips')
			self.last = t

	def on_fetch(self, mc, index, b):
		if self.verbose:
			print('fetch {:04x} {:02x}'.format(index, b))

	def on_decode(self, op, mnem):
		self.mnem = mnem
		if self.verbose:
			print(f'{mnem}')
		self.check_break(self.cpu.regs.pc)

	def dump(self):
		print(f'{str(self.cpu.regs)}')

	def add_break(self, addr, f):
		self.breaks[addr] = f

	def remove_break(self, addr):
		self.breaks.pop(addr, None)

	def check_break(self, addr):
		if (not self.prompt and addr in self.breaks) or self.step:
			self.step = False

			if addr in self.breaks:
				self.breaks[addr](self, self.cpu, addr)

			self.show_prompt(addr)

	def show_prompt(self, addr):
		print(f'break at {addr:04x}: {self.mnem}')

		self.prompt = True
		while True:
			cmd = sys.stdin.readline()
			if cmd == 'c':
				break
			elif cmd == 'n':
				self.step = True
				break
			elif cmd.startswith('p '):
				try:
					v = eval(cmd[2:])
					print(f'{v}')
				except Exception as e:
					print(f'{e}')
			elif cmd.startswith('h '):
				try:
					v = eval(cmd[2:])
					print(f'{v:04x}')
				except Exception as e:
					print(f'{e}')
			elif cmd.startswith('b '):
				try:
					bp = int(cmd[2:], 0)
					self.add_break(bp, dump)
					print(f'set bp {bp:04x}')
				except Exception as e:
					print(f'{e}')
			elif cmd.startswith('r '):
				try:
					if cmd == 'r ':
						bp = addr
					else:
						bp = int(cmd[2:], 0)
					self.remove_break(bp)
					print(f'unset bp {bp:04x}')
				except Exception as e:
					print(f'{e}')
			else:
				print(f'Unkown command: {cmd}')
		self.prompt = False


def dump(dbg, cpu, addr):
	dbg.dump()


def main():
	print('Starting gb...')

	dbg = PrintDebugger(verbose=False, perf=False)
	dbg.add_break(0x000a, dump)
	mc = MemCtrl()

	gpu = Gpu(hide=True)
	mc.add_hook(0xff40, 0xff4f, gpu.on_read, gpu.on_write)

	cpu = Cpu(mc, debugger=dbg)
	cpu.run()


if __name__ == '__main__':
	main()
