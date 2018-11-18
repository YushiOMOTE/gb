from abc import ABC, abstractmethod

import time
import sys
import cmd


class Debugger(ABC):
	@abstractmethod
	def on_start_cpu(self, cpu):
		pass

	@abstractmethod
	def on_start_gpu(self, gpu):
		pass

	@abstractmethod
	def before_exec(self):
		pass

	@abstractmethod
	def after_exec(self):
		pass

	@abstractmethod
	def on_fetch(self, mc, index, b):
		pass

	@abstractmethod
	def on_decode(self, op, mnem):
		pass

	@abstractmethod
	def on_read(self, addr, v):
		pass

	@abstractmethod
	def on_write(self, addr, v):
		pass


class DebugConfig(object):
	def __init__(self):
		self.gfx = True
		self.sound = True


class DebugShell(cmd.Cmd, Debugger):
	prompt = 'debug-shell$ '

	def __init__(self, init=False):
		super().__init__()

		self.initprompt = init
		self.last = None
		self.iters = 0
		self.cputrace = False
		self.cpuperf = False
		self.cpu = None
		self.breaks = set()
		self.watches = set()
		self.nobreak = False
		self.step = False
		self.mnem = None
		self.addr = None
		self.cfg = DebugConfig()
		self.gpu = None

	def on_start_cpu(self, cpu):
		self.cpu = cpu

		if self.cpu and self.gpu and self.initprompt:
			self.show_prompt()

	def on_start_gpu(self, gpu):
		self.gpu = gpu

		if self.cpu and self.gpu and self.initprompt:
			self.show_prompt()

	def before_exec(self):
		if self.cputrace:
			print(f'{str(self.cpu.regs)}')

	def after_exec(self):
		if not self.cpuperf:
			return

		self.iters += 1
		if self.iters % 10000 == 0:
			t = time.time()
			if self.last:
				print(f'{10000 / (t - self.last)} ips')
			self.last = t

	def on_fetch(self, mc, index, b):
		if self.cputrace:
			print('fetch {:04x} {:02x}'.format(index, b))

	def on_decode(self, op, mnem):
		self.mnem = mnem
		if self.cputrace:
			print(f'{mnem}')
		self.check_break(self.cpu.regs.pc)

	def on_read(self, addr, v):
		if not self.nobreak and addr in self.watches:
			print(f'read at {addr:04x}: {v:02x}')
			self.addr = addr
			self.show_prompt()

	def on_write(self, addr, v):
		if not self.nobreak and addr in self.watches:
			print(f'write at {addr:04x}: {v:02x}')
			self.addr = addr
			self.show_prompt()

	def dump(self):
		print(f'{str(self.cpu.regs)}')

	def add_break(self, addr):
		self.breaks.add(addr)

	def remove_break(self, addr):
		self.breaks.remove(addr)

	def add_watch(self, addr):
		self.watches.add(addr)

	def remove_watch(self, addr):
		self.watches.remove(addr)

	def check_break(self, addr):
		if (not self.nobreak and addr in self.breaks) or self.step:
			self.step = False
			self.addr = addr

			print(f'break at {addr:04x}: {self.mnem}')
			self.show_prompt()

	def show_prompt(self):
		self.nobreak = True
		self.cmdloop()
		self.nobreak = False

	def do_c(self, args):
		'Continue execution'
		print(f'continue')
		return True

	def do_n(self, args):
		'Execute forward one step'
		self.step = True
		return True

	def do_d(self, args):
		'Dump registers'
		self.dump()

	def do_p(self, args):
		'Print variable'
		try:
			v = self.eval(args)
			print(f'{v}')
		except Exception as e:
			print(f'{e}')

	def do_ph(self, args):
		'Print variable as hex'
		try:
			v = self.eval(args)
			print(f'{v:04x}')
		except Exception as e:
			print(f'{e}')

	def do_b(self, args):
		'Set break point'
		try:
			if args:
				bp = int(args, 0)
			else:
				bp = self.cpu.regs.pc
			self.add_break(bp)
			print(f'set break {bp:04x}')
		except Exception as e:
			print(f'{e}')

	def do_rb(self, args):
		'Remove break point'
		try:
			if args:
				bp = int(args, 0)
			else:
				bp = self.cpu.regs.pc
			self.remove_break(bp)
			print(f'remove break {bp:04x}')
		except Exception as e:
			print(f'{e}')

	def do_lb(self, args):
		'List break points'
		print('breaks:')
		for b in self.breaks:
			print(f'* {b:04x}')

	def do_w(self, args):
		'Add memory watch'
		try:
			if args:
				wp = int(args, 0)
			elif self.addr:
				wp = self.addr
			self.add_watch(wp)
			print(f'watch {wp:04x}')
		except Exception as e:
			print(f'{e}')

	def do_rw(self, args):
		'Remove memory watch'
		try:
			if args:
				wp = int(args, 0)
			elif self.addr:
				wp = self.addr
			self.remove_watch(wp)
			print(f'remove watch {wp:04x}')
		except Exception as e:
			print(f'{e}')

	def do_lw(self, args):
		'List memory watches'
		print('watches:')
		for w in self.watches:
			print(f'* {w:04x}')

	def do_ect(self, args):
		'Enable cpu tracing'
		self.cputrace = True
		print('Enabled cpu trace')

	def do_dct(self, args):
		'Disable cpu tracing'
		self.cputrace = False
		print('Disable cpu trace')

	def do_ecp(self, args):
		'Enable cpu perf'
		self.cpuperf = True
		print('Enabled cpu perf')

	def do_dcp(self, args):
		'Disable cpu perf'
		self.cpuperf = False
		print('Disabled cpu perf')

	def do_u(self, args):
		'Update debug config'
		args = args.split()
		try:
			p = args[0]
			v = args[1]
			if v == 't':
				v = True
			elif v == 'f':
				v = False
			else:
				v = eval(v)
			if hasattr(self.cfg, p):
				setattr(self.cfg, p, v)
				print(f'Set config "{p}" to "{v}"')
			else:
				print(f'No such param: {p}')
		except Exception as e:
			print(f'{e}')

	def do_cfg(self, args):
		'Show debug config'
		print('Debug config:')
		for k, v in self.cfg.__dict__.items():
			print(f'* {k}: {v}')

	def eval(self, s):
		r = self.cpu.regs
		f = self.cpu.regs.f
		m = self.cpu.mc
		d = self
		a = self.addr
		g = self.gpu
		return eval(s)
