import cmd
import rpyc
import threading
import socket


class Background(threading.Thread):
	def __init__(self, srv, port):
		super().__init__()
		self.srv = srv
		self.port = port

	def run(self):
		from rpyc.utils.server import ThreadedServer
		t = ThreadedServer(self.srv, port=self.port)
		t.start()


class DebugSubscriber(rpyc.Service):
	def __init__(self):
		super().__init__()

	def exposed_log(self, s):
		try:
			print(f'{s}')
		except Exception as e:
			print(f'Cannot print: {e}')


class DebugServer(rpyc.Service):
	def __init__(self):
		super().__init__()
		self.cli = None

	def on_connect(self, conn):
		pass

	def on_disconnect(self, conn):
		print(f'Debug client disconnected')
		self.cli = None

	def exposed_establish(self, h, p):
		print(f'Connect: {h}, {p}')
		self.cli = rpyc.connect(h, port=p)

	def exposed_b(self, arg):
		self.log(f'{arg}')

	def log(self, s):
		if self.cli:
			self.cli.root.log(s)


class DebugClient(cmd.Cmd):
	def __init__(self, host='localhost', port=18861):
		super().__init__()
		self.srv = rpyc.connect(host, port=port)
		h, p = self.srv._channel.stream.sock.getsockname()
		bg = Background(DebugSubscriber, p + 1)
		bg.start()
		self.establish(h, p + 1)

	def establish(self, h, p):
		self.srv.root.establish(h, p)

	def do_b(self, arg):
		self.srv.root.b(arg)

	def do_q(self, arg):
		print('quit')
		self.srv.close()
		return True


def run_debug_server():
	t = Background(DebugServer, 18861)
	t.start()


if __name__ == '__main__':
	run_debug_server()
	cli = DebugClient()
	cli.cmdloop()
