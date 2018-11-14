import yaml
import os
import re
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
	regs = cpu.regs
	{3}
	{4}
	regs.pc = (regs.pc + size) & 0xffff
	cpu.time += time
'''

# NOP
nop_tmpl = '''
	pass
'''

# INC16
inc16_tmpl = '''
	{0} = ({0} + 1) & 0xffff
'''

# DEC16
dec16_tmpl = '''
	{0} = ({0} + 0xffff) & 0xffff
'''

# INC8
inc8_tmpl = '''
	s, h, _, z = alu.add8({0}, 1)
	{0} = s
	flgs.h = h
	flgs.n = 0
	flgs.z = z
'''

# DEC8
dec8_tmpl = '''
	s, h, _, z = alu.sub8({0}, 1)
	{0} = s
	flgs.h = h
	flgs.n = 1
	flgs.z = z
'''

# LD t,f
ld_tmpl = '''
	{0} = {1}
'''

# LDD
ldd_tmpl = '''
	{} = {}
	regs.hl = (regs.hl + 0xffff) & 0xffff
'''

# LDI
ldi_tmpl = '''
	{} = {}
	regs.hl = (regs.hl + 1) & 0xffff
'''

# LGHL
ldhl_tmpl = '''
	s, h, c, z = alu.add16e({0}, {1})
	regs.hl = s
	flgs.h = h
	flgs.c = c
	flgs.z = 0
	flgs.n = 0
'''

# ADD16
add16_tmpl = '''
	s, h, c, z = alu.add16({0}, {1})
	{0} = s
	flgs.h = h
	flgs.c = c
	flgs.n = 0
'''

# ADD8
add8_tmpl = '''
	s, h, c, z = alu.add8({0}, {1})
	{0} = s
	flgs.h = h
	flgs.c = c
	flgs.n = 0
	flgs.z = z
'''

# ADD SP,n
addsp_tmpl = '''
	s, h, c, z = alu.add16e({0}, {1})
	{0} = s
	flgs.h = h
	flgs.c = c
	flgs.z = 0
	flgs.n = 0
'''

# ADC8
adc_tmpl = '''
	s, h, c, z = alu.add8({0}, {1}, flgs.c)
	{0} = s
	flgs.h = h
	flgs.c = c
	flgs.n = 0
	flgs.z = z
'''

# SUB
sub_tmpl = '''
	s, h, c, z = alu.sub8(regs.a, {0})
	regs.a = s
	flgs.h = h
	flgs.c = c
	flgs.n = 1
	flgs.z = z
'''

# SBC
sbc_tmpl = '''
	s, h, c, z = alu.sub8(regs.a, {0}, flgs.c)
	regs.a = s
	flgs.h = h
	flgs.c = c
	flgs.n = 1
	flgs.z = z
'''

# AND
and_tmpl = '''
	regs.a &= {}
	flgs.z = z(regs.a)
	flgs.n = 0
	flgs.h = 1
	flgs.c = 0
'''

# OR
or_tmpl = '''
	regs.a |= {}
	flgs.z = z(regs.a)
	flgs.n = 0
	flgs.h = 0
	flgs.c = 0
'''

# XOR
xor_tmpl = '''
	regs.a ^= {}
	flgs.z = z(regs.a)
	flgs.n = 0
	flgs.h = 0
	flgs.c = 0
'''

# CP
cp_tmpl = '''
	_, h, c, z = alu.sub8(regs.a, {0})
	flgs.z = z
	flgs.n = 1
	flgs.h = h
	flgs.c = c
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
	r = (l << 8) + h
	{0} = r
	flgs.z = z(r)
	flgs.n = 0
	flgs.h = 0
	flgs.c = 0
'''

# CPL
cpl_tmpl = '''
	regs.a ^= 0xff
	flgs.n = 0
	flgs.h = 0
'''

# CCF
ccf_tmpl = '''
	flgs.c ^= 1
	flgs.n = 0
	flgs.h = 0
'''

# SCF
scf_tmpl = '''
	flgs.c = 1
	flgs.n = 0
	flgs.h = 0
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
	v = {0}
	flgs.c = v & 0x80
	r = _rl(v, 8)
	{0} = r
	regs.f.z = z(r)
	regs.f.n = 0
	regs.f.h = 0
'''

# RLCA
rlca_tmpl = '''
	flgs.c = regs.a & 0x80
	regs.a = _rl(regs.a, 8)
	regs.f.z = 0
	regs.f.n = 0
	regs.f.h = 0
'''

# RL
rl_tmpl = '''
	v = {0} | (flgs.c << 8)
	r = _rl(v, 9) & 0xff
	{0} = r
	flgs.c = v & 0x10
	flgs.z = z(r)
	flgs.n = 0
	flgs.h = 0
'''

# RLA
rla_tmpl = '''
	v = regs.a | (flgs.c << 8)
	regs.a = _rl(v, 9) & 0xff
	flgs.c = v & 0x10
	flgs.z = 0
	flgs.n = 0
	flgs.h = 0
'''

# RRC
rrc_tmpl = '''
	v = {0}
	flgs.c = v & 1
	r = _rr(v, 8)
	{0} = r
	flgs.z = z(r)
	flgs.n = 0
	flgs.h = 0
'''

# RRCA
rrca_tmpl = '''
	flgs.c = regs.a & 1
	regs.a = _rr(regs.a, 8)
	flgs.z = 0
	flgs.n = 0
	flgs.h = 0
'''

# RR
rr_tmpl = '''
	x = {0}
	v = x << 1 | flgs.c
	v = _rr(v, 9)
	y = (v >> 1) & 0xff
	{0} = y
	flgs.c = v & 1
	flgs.z = z(y)
	flgs.n = 0
	flgs.h = 0
'''

# RRA
rra_tmpl = '''
	v = regs.a << 1 | flgs.c
	v = _rr(v, 9)
	regs.a = (v >> 1) & 0xff
	flgs.c = v & 1
	flgs.z = 0
	flgs.n = 0
	flgs.h = 0
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
	flgs.z = {1} | 1 << {0}
	regs.f.n = 0
	regs.f.h = 1
'''

# SET
set_tmpl = '''
	{1} |= (1 << {0})
'''

# RES
res_tmpl = '''
	{1} &= ~(1 << {0})
'''

# JP x
jp_tmpl = '''
	regs.pc = {}
	cpu.time += time
	return
'''

# JP x,y
jpif_tmpl = '''
	if {}:
		regs.pc = {}
		cpu.time += time[0]
	else:
		cpu.time += time[1]
	return
'''

# JR x
jr_tmpl = '''
	regs.pc += (alu.signed({}) + size) + 0xffff
	cpu.time += time
	return
'''

# JR x,y
jrif_tmpl = '''
	if {}:
		regs.pc = (regs.pc + alu.signed({}) + size) &  0xffff
		cpu.time += time[0]
	else:
		cpu.time += time[1]
	return
'''

# CALL x
call_tmpl = '''
	cpu.push(regs.pc + size)
	regs.pc = {}
	cpu.time += time
	return
'''

# CALL x,y
callif_tmpl = '''
	if {}:
		cpu.push(regs.pc + size)
		regs.pc = {}
		cpu.time += time[0]
	else:
		cpu.time += time[1]
	return
'''

# RST
rst_tmpl = '''
	regs.pc = {}
	cpu.time += time
	return
'''

# RET
ret_tmpl = '''
	regs.pc = cpu.pop()
	cpu.time += time
	return
'''

# RET x
retif_tmpl = '''
	if {}:
		regs.pc = cpu.pop()
		cpu.time += time[0]
	else:
		cpu.time += time[1]
	return
'''

# RETI
reti_tmpl = '''
	regs.pc = cpu.pop()
	cpu.intr = True
	cpu.time += time
	return
'''


def _eval(s, bits=8):
	if isinstance(s, int):
		return s

	s = s.lower()

	if s == 'z':
		return f'flgs.z'
	elif s == 'nz':
		return f'~flgs.z'
	elif s == 'cf':
		return f'flgs.c'
	elif s == 'nc':
		return f'~flgs.c'

	if s.startswith('('):
		s = s[1:-1]
		return f'mc.as{bits}[{_eval(s, bits)}]'

	v = []
	for i in s.split('+'):
		if i == 'a8' or i == 'd8':
			v.append('mc.fetch()')
		elif i == 'a16' or i == 'd16':
			v.append('mc.fetch16()')
		elif i == 'r8':
			v.append('alu.signed(mc.fetch())')
		else:
			try:
				v.append(f'{int(i, 0)}')
			except:
				v.append(f'regs.{i}')
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


def _prepare(body):
	s = ''
	if 'flgs' in body:
		s += 'flgs = cpu.regs.f\n\t'
	if 'mc' in body:
		s += 'mc = cpu.mc\n\t'
	return s


def _set_flag(s, f, v):
	if f != '_':
		if f != '0':
			if f == '1':
				s.append(f'0x{v:02x}')
			else:
				s.append(f'(0x{v:02x} if {f} else 0)')
		return 0
	else:
		return v


def _expand_macro(body):
	exp = r'flg\(([^,]*),([^,]*),([^,]*),([^,]*)\)'
	m = re.search(exp, body)
	if m is None:
		return body
	z = m.group(1).strip()
	n = m.group(2).strip()
	h = m.group(3).strip()
	c = m.group(4).strip()
	s = []
	m = 0
	m |= _set_flag(s, z, 0x80)
	m |= _set_flag(s, n, 0x40)
	m |= _set_flag(s, h, 0x20)
	m |= _set_flag(s, c, 0x10)
	s = '|'.join(s)
	return re.sub(exp, body, f'({s}) & 0x{m:02x}')


def _i(i, debug=False):
	tmpl = globals()[f'{i.op}_tmpl']
	body = _f(tmpl, *[_eval(a, i.bits) for a in i.args])
	prep = _prepare(body)
	method = _f(base_tmpl, i.code, repr(i.size), repr(i.time), prep, body)

	if debug:
		print(f'# {i.code:02x}: {i.op} {",".join([str(s) for s in i.args])}')
		print(method)

	exec(method, globals())

	if i.code > 0xff:
		f = f'op_{i.code:04x}'
	else:
		f = f'op_{i.code:02x}'
	ops[i.code] = globals()[f]


ops = {}
mnemonics = {}


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

		#print(f'Generate {i.code:02x}: {i.op} {i.args}')

		args = [str(a) for a in i.args]
		mnemonics[i.code] = f'{i.op} {",".join(args)}'

		if i.code == 0xe8:
			i.op = 'addsp'
			_i(i)
		elif i.op == 'inc' or i.op == 'dec' or i.op == 'add':
			i.suffix()
			_i(i)
		elif isinstance(i.time, list):
			i.op = f'{i.op}if'
			_i(i)
		else:
			_i(i)


def op(cpu, op, debugger=None):
	if debugger:
		debugger.on_decode(op, f'{mnemonics.get(op, "unkown op")}')

	ops[op](cpu)


_load()
