import yaml
import os
import numpy as np


# check nth-bit carry carry on add
def ca(x, y, n):
	b = (1 << n)
	m = b - 1
	c = ((x & m) + (y & m)) & b
	if c == b:
		return 1
	return 0


# check nth-bit carry on sub
def cs(x, y, n):
	b = (1 << n)
	m = b - 1
	c = (b + (x & m) - (y & m)) & b
	if c == 0:
		return 0
	return 1


def z(v):
	if v == 0:
		return 1
	return 0


def add_sp(cpu, v):
	sp = cpu.regs.sp
	if v >= 0:
		vv = v
		cpu.regs.f.h |= ca(sp, vv, 12)
		cpu.regs.f.c |= ca(sp, vv, 16)
		return cpu.regs.sp + vv
	else:
		vv = abs(v)
		cpu.regs.f.h |= cs(sp, vv, 12)
		cpu.regs.f.c |= cs(sp, vv, 16)
		return cpu.regs.sp - vv


def _rl(n, b):
	b = n & (1 << (b - 1))
	n <<= 1
	if b:
		n |= 1
	n &= ((1 << b) - 1)
	return n


def _rr(n, b):
	n &= ((1 << b) - 1)
	b = n & 1
	n >>= 1
	if b:
		n |= (1 << (b - 1))
	return n


base_tmpl = '''
def op_{:02x}(cpu):
	{}
'''

# NOP
nop_tmpl = '''
	pass
'''

# INC16
inc16_tmpl = '''
	{} += 1
'''

# DEC16
dec16_tmpl = '''
	{} -= 1
'''

# INC8
inc8_tmpl = '''
	cpu.regs.f.h |= ca({0}, 1, 4)
	{0} += 1
	cpu.regs.f.n = 0
	cpu.regs.f.z |= z({0})
'''

# DEC8
dec8_tmpl = '''
	cpu.regs.f.h |= cs({0}, 1, 4)
	{0} -= 1
	cpu.regs.f.n = 1
	cpu.regs.f.z |= z({0})
'''

# LD t,f
ld_tmpl = '''
	{} = {}
'''

# LDD
ldd_tmpl = '''
	{} = {}
	cpu.regs.hl -= 1
'''

# LDI
ldi_tmpl = '''
	{} = {}
	cpu.regs.hl += 1
'''

# LGHL
ldhl_tmpl = '''
	# {0}, {1}
	cpu.regs.hl = add_sp(cpu, cpu.fetch())
	cpu.regs.f.z = 0
	cpu.regs.f.n = 0
'''

# ADD16
add16_tmpl = '''
	v = {1}
	cpu.regs.f.h |= ca({0}, v, 12)
	cpu.regs.f.c |= ca({0}, v, 16)
	{0} += v
	cpu.regs.f.n = 0
'''

# ADD SP,n
addsp_tmpl = '''
	v = np.int8({1})
	cpu.regs.sp = add_sp(cpu, v)
	cpu.regs.f.z = 0
	cpu.regs.f.n = 0
'''

# ADD8
add8_tmpl = '''
	v = {1}
	cpu.regs.f.h |= ca({0}, v, 4)
	cpu.regs.f.c |= ca({0}, v, 8)
	{0} += v
	cpu.regs.f.n = 0
	cpu.regs.f.z = z({0})
'''

# ADC8
adc8_tmpl = '''
	v = {1}
	c = cpu.regs.c
	cpu.regs.f.h |= ca({0}, v + c, 4)
	cpu.regs.f.c |= ca({0}, v + c, 8)
	{0} += (v + c)
	cpu.regs.f.n = 0
	cpu.regs.f.z = z({0})
'''

# SUB8
sub8_tmpl = '''
	v = {1}
	cpu.regs.f.h |= cs({0}, v, 4)
	cpu.regs.f.c |= cs({0}, v, 8)
	{0} -= v
	cpu.regs.f.n = 1
	cpu.regs.f.z = z({0})
'''

# SBC8
sbc8_tmpl = '''
	v = {1}
	cpu.regs.f.h |= cs({0}, v + c, 4)
	cpu.regs.f.c |= cs({0}, v + c, 8)
	{0} -= (v + c)
	cpu.regs.f.n = 1
	cpu.regs.f.z = z({0})
'''

# AND
and_tmpl = '''
	cpu.regs.a &= {}
	cpu.regs.f.z = z(cpu.regs.a)
	cpu.regs.f.n = 0
	cpu.regs.f.h = 1
	cpu.regs.f.c = 0
'''

# OR
or_tmpl = '''
	cpu.regs.a |= {}
	cpu.regs.f.z = z(cpu.regs.a)
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
	cpu.regs.f.c = 0
'''

# XOR
xor_tmpl = '''
	cpu.regs.a ^= {}
	cpu.regs.f.z = z(cpu.regs.a)
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
	cpu.regs.f.c = 0
'''

# CP
cp_tmpl = '''
	v = {0}
	a = cpu.regs.a
	cpu.regs.f.z = z(a - v)
	cpu.regs.f.n = 1
	cpu.regs.f.h |= cs(a, v, 4)
	cpu.regs.f.c |= cs(a, v, 8)
'''


def _push(cpu, v):
	cpu.mc[cpu.regs.sp - 1] = (v >> 8) & 0xff
	cpu.mc[cpu.regs.sp - 2] = v & 0xff
	cpu.regs.sp -= 2


def _pop(cpu):
	v = cpu.mc[cpu.regs.sp] & 0xff
	v |= (cpu.mc[cpu.regs.sp + 1] << 8) & 0xff00
	cpu.regs.sp += 2
	return v


# PUSH
push_tmpl = '''
	_push(cpu, {0})
'''

# POP
pop_tmpl = '''
	{0} = _pop(cpu)
'''

# SWAP
swap_impl = '''
	v = {0}
	h = (v >> 8) & 0xf
	l = v & 0xf
	{0} = (l << 8) + h
	cpu.regs.f.z = z({0})
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
	cpu.regs.f.c = 0
'''

# CPL
cpl_tmpl = '''
	cpu.regs.a ^= 0xff
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
'''

# CCF
ccf_tmpl = '''
	cpu.regs.f.c ^= 1
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
'''

# SCF
scf_tmpl = '''
	cpu.regs.f.c = 1
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
'''

# HALT
halt_tmpl = '''
	cpu.halt = True
'''

# STOP
stop_tmpl = '''
	cpu.stop = True
'''

# DI
di_tmpl = '''
	cpu.di = True
'''

# EI
ei_impl = '''
	cpu.ei = True
'''

# RLC
rlc_tmpl = '''
	cpu.regs.f.c = {0} & 0x80
	{0} = _rl({0}, 8)
	cpu.regs.f.z = z({0})
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
'''

# RL
rl_tmpl = '''
	v = {0} | (cpu.regs.f.c << 8)
	{0} = _rl(v, 9) & 0xff
	cpu.regs.f.c = v & 0x10
	cpu.regs.f.z = z({0})
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
'''

# RRC
rrc_tmpl = '''
	cpu.regs.f.c = {0} & 1
	{0} = _rr({0}, 8)
	cpu.regs.f.z = z({0})
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
'''

# RR
rr_tmpl = '''
	v = {0} << 1 | cpu.regs.f.c
	v = _rr(v, 9)
	{0} = (v >> 1) & 0xff
	cpu.regs.f.c = v & 1
	cpu.regs.f.z = z({0})
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
'''

# BIT
bit_tmpl = '''
	cpu.regs.f.z = z({1} | 1 << {0})
	cpu.regs.f.n = 0
	cpu.regs.f.h = 1
'''

# SET
set_tmpl = '''
	{1} |= (1 << {0})
'''

# RES
res_tmpl = '''
	{1} &= np.uint8(~(1 << {0}))
'''

# JP x
jp_tmpl = '''
	cpu.regs.pc = {}
'''

# JP x,y
jpif_tmpl = '''
	if {}:
		cpu.regs.pc = {}
'''

# JR x
jr_tmpl = '''
	cpu.regs.pc += np.int8({})
'''

# JR x,y
jrif_tmpl = '''
	if {}:
		cpu.regs.pc += np.int8({})
'''

# CALL x
call_tmpl = '''
	_push(cpu, cpu.regs.pc)
	cpu.regs.pc = {}
'''

# CALL x,y
callif_tmpl = '''
	if {}:
		_push(cpu, cpu.regs.pc)
		cpu.regs.pc = {}
'''

# RST
rst_tmpl = '''
	cpu.regs.pc = {}
'''

# RET
ret_impl = '''
	cpu.regs.pc = _pop(cpu)
'''

# RET x
retif_impl = '''
	if {}:
		cpu.regs.pc = _pop(cpu)
'''

# RETI
reti_impl = '''
	cpu.regs.pc = _pop(cpu)
	cpu.intr = True
'''


def _inc(cpu, r):
	a = getattr(cpu.regs, r)
	setattr(cpu.regs, r, a + 1)
	return a


def _dec(cpu, r):
	a = getattr(cpu.regs, r)
	setattr(cpu.regs, r, a - 1)
	return a


def _eval(s):
	s = s.lower()

	if s == 'z':
		return f'cpu.regs.f.z'
	elif s == 'nz':
		return f'~cpu.regs.f.z'
	elif s == 'cf':
		return f'cpu.regs.f.c'
	elif s == 'nc':
		return f'~cpu.regs.f.c'

	if s.startswith('('):
		s = s[1:-1]
		return f'cpu.mc[{_eval(s)}]'

	v = []
	for i in s.split('+'):
		if i == 'a8' or i == 'd8':
			v.append('cpu.fetch()')
		elif i == 'a16' or i == 'd16':
			v.append('cpu.fetch16()')
		elif i == 'r8':
			v.append('np.int8(cpu.fetch())')
		else:
			try:
				v.append(f'{int(i, 0)}')
			except:
				v.append(f'cpu.regs.{i}')
	return '+'.join(v)


def _f(s, *args):
	return s.format(*args)


def _i(op, type, *args, debug=False):
	tmpl = globals()[f'{type}_tmpl']
	body = _f(tmpl, *[_eval(i) for i in args])
	method = _f(base_tmpl, op, body)
	if debug:
		print(f'# {op:02x}: {type} {",".join(args)}')
		print(method)
	exec(method, globals())


def _load():
	path = os.path.dirname(os.path.abspath(__file__))

	with open(f'{path}/inst.yml', 'r') as f:
		try:
			insts = yaml.load(f.read())
		except yaml.YAMLError as e:
			print(f'{e}')

	for i in insts:
		code = i['code']
		op = i['operator']
		args = i['operands']
		bits = i['bits']

		# print(f'Generate {code:02x}: {op} {args}')

		if op == 'ldhl' or op == 'ldd' or op == 'ldi' or op == 'ld':
			_i(code, op, *args, debug=True)

		elif op == 'inc' or op == 'dec':
			_i(code, f'{op}{bits}', *args, debug=True)

		elif op == 'push' or op == 'pop':
			_i(code, op, *args, debug=True)

		elif op == 'add':
			if code == 0xe8:
				_i(code, 'addsp', *args, debug=True)
			else:
				_i(code, f'{op}{bits}', *args, debug=True)


def op(cpu, op):
	if op > 0xff:
		f = f'op_{op:04x}'
	else:
		f = f'op_{op:02x}'
	globals()[f](cpu)


_load()
