import unittest

tests = ['alu', 'cpu']
tests = [f'test.test_{t}' for t in tests]
tests = [unittest.defaultTestLoader.loadTestsFromName(t) for t in tests]
tests = unittest.TestSuite(tests)

runner = unittest.TextTestRunner().run(tests)
