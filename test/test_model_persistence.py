import pprint
import unittest
from mock import MagicMock, patch
from klue.swagger.api import API


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
    x-persist: klue.test.PersistentFoo
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
        api = API('somename', yaml_str=yaml_str)

        Foo = api.model.Foo
        self.assertTrue(hasattr(Foo, 'load_from_db'))

        f = Foo()
        f.save_to_db()
        self.assertTrue(hasattr(f, 'save_to_db'))


    @patch("klue.test.PersistentFoo.load_from_db")
    def test_load_from_db(self, m):
        m.return_value = 'foobar'

        api = API('somename', yaml_str=yaml_str)

        f = api.model.Foo.load_from_db(1, 2, a=1, b=2)

        m.assert_called_once_with(1, 2, a=1, b=2)
        self.assertEqual(f, 'foobar')

    @patch("klue.test.PersistentFoo.load_from_db")
    def test_load_from_db__return_tupple(self, m):
        m.return_value = ('foobar', 'barbaz')

        api = API('somename', yaml_str=yaml_str)

        a, b = api.model.Foo.load_from_db(1, 2, a=1, b=2)

        m.assert_called_once_with(1, 2, a=1, b=2)
        self.assertEqual(a, 'foobar')
        self.assertEqual(b, 'barbaz')

    @patch("klue.test.PersistentFoo.save_to_db")
    def test_save_to_db(self, m):
        api = API('somename', yaml_str=yaml_str)

        f = api.model.Foo()
        f.save_to_db(1, 2, a=1, b=2)

        m.assert_called_once_with(f, 1, 2, a=1, b=2)
