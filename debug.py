from abc import ABC, abstractmethod


class Debugger(ABC):
	@abstractmethod
	def on_start(self, cpu):
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
