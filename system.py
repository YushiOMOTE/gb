from cpu import Cpu, MemCtrl
from gpu import Gpu
from debug import DebugShell


def main():
	print('Starting gb...')

	dbg = DebugShell(init=True)

	mc = MemCtrl(debugger=dbg)

	cpu = Cpu(mc, debugger=dbg)

	gpu = Gpu(mc, debugger=dbg, show=True)

	cpu.setup()
	gpu.setup()

	while True:
		clk = cpu.step()
		gpu.step(clk)


if __name__ == '__main__':
	main()
