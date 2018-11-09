import yaml
import os

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
		return 1
	return 0


def z(v):
	if v == 0:
		return 1
	return 0


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

# ADD16
add16_tmpl = '''
	cpu.regs.f.h |= ca({0}, {1}, 12)
	cpu.regs.f.c |= ca({0}, {1}, 16)
	{0} += {1}
	cpu.regs.f.n = 0
'''

# ADD8
add8_tmpl = '''
	cpu.regs.f.h |= ca({0}, {1}, 4)
	cpu.regs.f.c |= ca({0}, {1}, 8)
	{0} += {1}
	cpu.regs.f.n = 0
	cpu.regs.f.z = z({0})
'''

# ADC8
adc8_tmpl = '''
	c = cpu.regs.c
	cpu.regs.f.h |= ca({0}, {1} + c, 4)
	cpu.regs.f.c |= ca({0}, {1} + c, 8)
	{0} += ({1} + c)
	cpu.regs.f.n = 0
	cpu.regs.f.z = z({0})
'''

# SUB8
sub8_tmpl = '''
	cpu.regs.f.h |= cs({0}, {1}, 4)
	cpu.regs.f.c |= cs({0}, {1}, 8)
	{0} -= {1}
	cpu.regs.f.n = 1
	cpu.regs.f.z = z({0})
'''

# PUSH
push_tmpl = '''
	cpu.mc[cpu.regs.sp - 1] = ({0} >> 8) & 0xff
	cpu.mc[cpu.regs.sp - 2] = {0} & 0xff
	cpu.regs.sp -= 2
'''

# POP
pop_tmpl = '''
	v = cpu.mc[cpu.regs.sp] & 0xff
	v |= (cpu.mc[cpu.regs.sp + 1] << 8) & 0xff00
	{0} = v
	cpu.regs.sp += 2
'''

def _inc(cpu, r):
	a = getattr(cpu.regs, r)
	setattr(cpu.regs, r, a + 1)
	return a


def _dec(cpu, r):
	a = getattr(cpu.regs, r)
	setattr(cpu.regs, r, a - 1)
	return a

def _eval(s, off=None):
	s = s.lower()

	if s.startswith('('):
		s = s[1:-1]
		off = f' + 0x{off:04x}' if off else ''
		return f'cpu.mc[{_eval(s)}{off}]'

	if s.endswith('+'):
		s = s[0:-1]
		return f'_inc(cpu, "{s}")'
	elif s.endswith('-'):
		s = s[0:-1]
		return f'_dec(cpu, "{s}")'

	v = []
	for i in s.split('+'):
		if i == 'n':
			v.append('cpu.fetch()')
		elif i == 'nn':
			v.append('cpu.fetch16()')
		else:
			try:
				v.append(f'{int(i, 0)})')
			except:
				v.append(f'cpu.regs.{i}')
	return '+'.join(v)


def _f(s, *args):
	return s.format(*args)


def _i(op, type, *args, debug=False, off=None):
	tmpl = globals()[f'{type}_tmpl']
	body = _f(tmpl, *[_eval(i, off=off) for i in args])
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

		if op == 'ld' or op == 'ldh':
			if code == 0xe2 or \
			   code == 0xf2 or \
			   op == 'ldh':
				off = 0xff00
			else:
				off = None

			_i(code, 'ld', *args, off=off)

		elif op == 'inc' or op == 'dec':
			_i(code, f'{op}{bits}', *args, debug=True)

		elif op == 'push' or op == 'pop':
			_i(code, op, *args, debug=True)


def op(cpu, op):
	if op > 0xff:
		f = f'op_{op:04x}'
	else:
		f = f'op_{op:02x}'
	globals()[f](cpu)


_load()
