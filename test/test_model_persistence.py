import unittest
from mock import patch
from pymacaron_core.swagger.api import API


#
# Swagger spec
#

yaml = """
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
    x-persist: pymacaron_core.test.PersistentFoo
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

    def test_x_persist(self):
        api = API('somename', yaml_str=yaml)

        Foo = api.model.Foo
        self.assertTrue(hasattr(Foo, 'load_from_db'))
        self.assertEqual(Foo.load_from_db(), 'bob')

        f = Foo()
        self.assertTrue(hasattr(f, 'save_to_db'))
        self.assertEqual(f.save_to_db(), 'foo')
