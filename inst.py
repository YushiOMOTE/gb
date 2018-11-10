import yaml
import os
import numpy as np
import functools

import alu


def z(v):
	if v == 0:
		return 1
	return 0


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
def op_{0:02x}(cpu, size={1}, time={2}):
	{3}
	cpu.regs.pc += size
	cpu.time += time
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
	s, [h, _], z = alu.add8({0}, 1)
	{0} = s
	cpu.regs.f.h = h
	cpu.regs.f.n = 0
	cpu.regs.f.z = z
'''

# DEC8
dec8_tmpl = '''
	s, [h, _], z = alu.sub8({0}, 1)
	{0} = s
	cpu.regs.f.h = h
	cpu.regs.f.n = 1
	cpu.regs.f.z = z
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
	s, [h, _], z = alu.add16e({0}, {1})
	cpu.regs.hl = s
	cpu.regs.f.z = 0
	cpu.regs.f.n = 0
'''

# ADD16
add16_tmpl = '''
	s, [h, c], z = alu.add16({0}, {1})
	{0} = s
	cpu.regs.f.h = h
	cpu.regs.f.c = c
	cpu.regs.f.n = 0
'''

# ADD8
add8_tmpl = '''
	s, [h, c], z = alu.add8({0}, {1})
	{0} = s
	cpu.regs.f.h = h
	cpu.regs.f.c = c
	cpu.regs.f.n = 0
	cpu.regs.f.z = z
'''

# ADD SP,n
addsp_tmpl = '''
	s, [h, c], z = alu.add16e({0}, {1})
	cpu.regs.f.h = h
	cpu.regs.f.c = c
	cpu.regs.f.z = 0
	cpu.regs.f.n = 0
'''

# ADC8
adc_tmpl = '''
	s, [h, c], z = alu.add8({0}, {1}, cpu.regs.f.c)
	{0} = s
	cpu.regs.f.h = h
	cpu.regs.f.c = c
	cpu.regs.f.n = 0
	cpu.regs.f.z = z
'''

# SUB
sub_tmpl = '''
	s, [h, c], z = alu.sub8(cpu.regs.a, {0})
	cpu.regs.a = s
	cpu.regs.f.h = h
	cpu.regs.f.c = c
	cpu.regs.f.n = 1
	cpu.regs.f.z = z
'''

# SBC
sbc_tmpl = '''
	s, [h, c], z = alu.sub8(cpu.regs.a, {0}, cpu.regs.f.c)
	cpu.regs.a = s
	cpu.regs.f.h = h
	cpu.regs.f.c = c
	cpu.regs.f.n = 1
	cpu.regs.f.z = z
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
	_, [h, c], z = alu.sub8(cpu.regs.a, {0})
	cpu.regs.f.z = z
	cpu.regs.f.n = 1
	cpu.regs.f.h = h
	cpu.regs.f.c = c
'''

# PUSH
push_tmpl = '''
	cpu.push({0})
'''

# POP
pop_tmpl = '''
	{0} = cpu.pop()
'''

# SWAP
swap_tmpl = '''
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
ei_tmpl = '''
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

# RLCA
rlca_tmpl = '''
	cpu.regs.f.c = cpu.regs.a & 0x80
	cpu.regs.a = _rl(cpu.regs.a, 8)
	cpu.regs.f.z = 0
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

# RLA
rla_tmpl = '''
	v = cpu.regs.a | (cpu.regs.f.c << 8)
	cpu.regs.a = _rl(v, 9) & 0xff
	cpu.regs.f.c = v & 0x10
	cpu.regs.f.z = 0
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

# RRCA
rrca_tmpl = '''
	cpu.regs.f.c = cpu.regs.a & 1
	cpu.regs.a = _rr(cpu.regs.a, 8)
	cpu.regs.f.z = 0
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

# RRA
rra_tmpl = '''
	v = cpu.regs.a << 1 | cpu.regs.f.c
	v = _rr(v, 9)
	cpu.regs.a = (v >> 1) & 0xff
	cpu.regs.f.c = v & 1
	cpu.regs.f.z = 0
	cpu.regs.f.n = 0
	cpu.regs.f.h = 0
'''

# SLA
sla_tmpl = '''
	raise Exception('sla not implemented')
'''

# SRA
sra_tmpl = '''
	raise Exception('sra not implemented')
'''

# SRL
srl_tmpl = '''
	raise Exception('sla not implemented')
'''

# SRR
srr_tmpl = '''
	raise Exception('sra not implemented')
'''

# DAA
daa_tmpl = '''
	raise Exception('daa not implemented')
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
	cpu.push(cpu.regs.pc)
	cpu.regs.pc = {}
'''

# CALL x,y
callif_tmpl = '''
	if {}:
		cpu.push(cpu.regs.pc)
		cpu.regs.pc = {}
'''

# RST
rst_tmpl = '''
	cpu.regs.pc = {}
'''

# RET
ret_tmpl = '''
	cpu.regs.pc = cpu.pop()
'''

# RET x
retif_tmpl = '''
	if {}:
		cpu.regs.pc = cpu.pop()
'''

# RETI
reti_tmpl = '''
	cpu.regs.pc = cpu.pop()
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


def _eval(s, bits=8):
	if isinstance(s, int):
		return s

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
		return f'cpu.mc.as{bits}[{_eval(s, bits)}]'

	v = []
	for i in s.split('+'):
		if i == 'a8' or i == 'd8':
			v.append('cpu.mc.fetch()')
		elif i == 'a16' or i == 'd16':
			v.append('cpu.mc.fetch16()')
		elif i == 'r8':
			v.append('np.int8(cpu.mc.fetch())')
		else:
			try:
				v.append(f'{int(i, 0)}')
			except:
				v.append(f'cpu.regs.{i}')
	return '+'.join(v)


class Inst:
	def __init__(self, d):
		self.code = d['code']
		self.op = d['operator']
		self.args = d['operands']
		self.bits = d['bits'] or 16
		self.time = d['time']
		self.size = d['size']

	def suffix(self):
		self.op = f'{self.op}{self.bits}'


def _f(s, *args):
	return s.format(*args)


def _i(i, debug=False):
	tmpl = globals()[f'{i.op}_tmpl']
	body = _f(tmpl, *[_eval(a, i.bits) for a in i.args])
	method = _f(base_tmpl, i.code, repr(i.size), repr(i.time), body)
	if debug:
		print(f'# {i.code:02x}: {i.op} {",".join(i.args)}')
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
		i = Inst(i)

		if i.op == 'prefix':
			continue

		print(f'Generate {i.code:02x}: {i.op} {i.args}')

		if i.code == 0xe8:
			i.op = 'addsp'
			_i(i)
		elif i.op == 'inc' or \
			 i.op == 'dec' or \
			 i.op == 'add':
			i.suffix()
			_i(i)
		else:
			_i(i)

def op(cpu, op):
	if op > 0xff:
		f = f'op_{op:04x}'
	else:
		f = f'op_{op:02x}'
	globals()[f](cpu)


_load()
