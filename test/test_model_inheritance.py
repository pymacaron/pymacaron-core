import unittest
from pymacaron_core.swagger.api import API


#
# Swagger spec
#

yaml_str = """
swagger: '2.0'
info:
  version: '0.0.1'
host: some.server.com
schemes:
  - http
produces:
  - application/json
definitions:
  Foo:
    type: object
    description: a foo
    x-parent: pymacaron_core.test.FunnyDad
    properties:
      foo:
        type: string
        format: foo
        description: bar
"""

#
# Tests
#

class Tests(unittest.TestCase):

    def test_x_parent(self):
        api = API('somename', yaml_str=yaml_str)

        Foo = api.model.Foo
        f = Foo()
        self.assertTrue(hasattr(f, 'lol'))
        self.assertTrue(hasattr(f, 'roflol'))
        self.assertEqual(f.lol(), 'lol')
        self.assertEqual(f.roflol(), 'roflol')
