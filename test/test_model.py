import unittest
from pymacaron_core.swagger.api import API
from pymacaron_core.models import get_model
from pymacaron_core.models import PyMacaronModel


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
    properties:
      s:
        type: string
      i:
        type: integer
      o:
        $ref: '#/definitions/Bar'
      lst:
        type: array
        items:
          type: string
      lo:
        type: array
        items:
          $ref: '#/definitions/Bar'

  Bar:
    type: object
    properties:
      s:
        type: string
      o:
        $ref: '#/definitions/Baz'

  Baz:
    type: object
    properties:
      s:
        type: string

"""

#
# Tests
#

class Tests(unittest.TestCase):

    def setUp(self):
        API('somename', yaml_str=yaml_str)


    def test__setattr__getattr(self):
        o = get_model('Foo')()

        # set/get a bravado attribute
        self.assertEqual(o.s, None)
        self.assertEqual(getattr(o, 's'), None)

        o.s = 'bob'
        self.assertEqual(o.s, 'bob')
        self.assertEqual(getattr(o, 's'), 'bob')

        # Make sure it's really the Bravado instance's attribute that was updated
        self.assertTrue('s' not in dir(o))
        self.assertEqual(getattr(o, '__bravado_instance').s, 'bob')

        o.s = None
        self.assertEqual(o.s, None)
        self.assertEqual(getattr(o, 's'), None)

        setattr(o, 's', 'bob')
        self.assertTrue('s' not in dir(o))
        self.assertEqual(getattr(o, '__bravado_instance').s, 'bob')
        self.assertEqual(o.s, 'bob')
        self.assertEqual(getattr(o, 's'), 'bob')

        setattr(o, 's', None)
        self.assertTrue('s' not in dir(o))
        self.assertEqual(getattr(o, '__bravado_instance').s, None)
        self.assertEqual(o.s, None)
        self.assertEqual(getattr(o, 's'), None)

        # set/get a local attribute
        with self.assertRaises(Exception) as context:
            o.local
        self.assertTrue("Model 'Foo' has no attribute local" in str(context.exception))

        with self.assertRaises(Exception) as context:
            getattr(o, 'local')
        self.assertTrue("Model 'Foo' has no attribute local" in str(context.exception))

        o.local = 'bob'
        self.assertTrue('local' in dir(o))
        self.assertEqual(o.local, 'bob')
        self.assertEqual(getattr(o, 'local'), 'bob')

        o.local = None
        self.assertEqual(o.local, None)
        self.assertEqual(getattr(o, 'local'), None)

        setattr(o, 'local', 'bob')
        self.assertEqual(o.local, 'bob')
        self.assertEqual(getattr(o, 'local'), 'bob')

        setattr(o, 'local', None)
        self.assertEqual(o.local, None)
        self.assertEqual(getattr(o, 'local'), None)


    def test__hasattr(self):
        o = get_model('Foo')()

        self.assertTrue(hasattr(o, 's'))
        self.assertFalse(hasattr(o, 'local'))

        o.local = None
        self.assertTrue(hasattr(o, 'local'))


    def test__delattr(self):
        o = get_model('Foo')()

        o.s = 'bob'
        self.assertEqual(o.s, 'bob')
        del o.s
        self.assertTrue(hasattr(o, 's'))
        self.assertEqual(o.s, None)

        o.s = 'bob'
        self.assertEqual(o.s, 'bob')
        delattr(o, 's')
        self.assertTrue(hasattr(o, 's'))
        self.assertEqual(o.s, None)

        o.local = 'bob'
        self.assertEqual(o.local, 'bob')
        del o.local
        self.assertFalse(hasattr(o, 'local'))
        with self.assertRaises(Exception) as context:
            o.local
        self.assertTrue("Model 'Foo' has no attribute local" in str(context.exception))

        o.local = 'bob'
        self.assertEqual(o.local, 'bob')
        delattr(o, 'local')
        self.assertFalse(hasattr(o, 'local'))
        with self.assertRaises(Exception) as context:
            o.local
        self.assertTrue("Model 'Foo' has no attribute local" in str(context.exception))


    def test__getitem__setitem__delitem(self):
        o = get_model('Foo')()
        self.assertEqual(o.s, None)
        self.assertEqual(o['s'], None)

        o['s'] = 'bob'
        self.assertEqual(o.s, 'bob')
        self.assertEqual(o['s'], 'bob')

        o['s'] = None
        self.assertEqual(o.s, None)
        self.assertEqual(o['s'], None)

        o['s'] = 'bob'
        self.assertEqual(o.s, 'bob')
        del o['s']
        self.assertEqual(o.s, None)

        # But local attributes may not be set this way
        with self.assertRaises(Exception) as context:
            o['local']
        self.assertTrue("Model 'Foo' has no attribute local" in str(context.exception))

        with self.assertRaises(Exception) as context:
            o['local'] = 123
        self.assertTrue("Model 'Foo' has no attribute local" in str(context.exception))

        with self.assertRaises(Exception) as context:
            del o['local']
        self.assertTrue("Model 'Foo' has no attribute local" in str(context.exception))


    def test__eq(self):
        Foo = get_model('Foo')
        Bar = get_model('Bar')
        a = Foo(s='abc', i=12, o=Bar(s='def'))
        b = Foo(s='abc', i=12, o=Bar(s='def'))

        self.assertEqual(a, b)
        self.assertNotEqual(a, 'bob')

        # Adding local parameters does not affect eq
        a.local = 'whatever'
        self.assertEqual(a, b)

        # Changing bravado values makes them different
        a.o.s = '123'
        self.assertNotEqual(a, b)


    def test__to_json__from_json(self):
        Foo = get_model('Foo')
        Bar = get_model('Bar')
        Baz = get_model('Baz')
        a = Foo(
            s='abc',
            i=12,
            lst=['a', 'b', 'c'],
            o=Bar(
                s='1',
                o=Baz(
                    s='2'
                )
            ),
            lo=[
                Baz(s='r'),
                Baz(s='t'),
                Baz(s='u'),
                Baz(),
            ]
        )
        self.assertTrue(isinstance(a, PyMacaronModel))

        j = a.to_json()
        self.assertEqual(
            j,
            {
                's': 'abc',
                'i': 12,
                'lst': ['a', 'b', 'c'],
                'o': {'o': {'s': '2'}, 's': '1'},
                'lo': [{'s': 'r'}, {'s': 't'}, {'s': 'u'}, {}],
            }
        )

        o = Foo.from_json(j)
        self.assertTrue(isinstance(o, PyMacaronModel))
        # TODO: o now has multiple attributes set to None, while a lacks them,
        # and bravado's __eq__ does not see None and absence as equal...
        # self.assertEqual(o, a)

        jj = o.to_json()
        self.assertEqual(jj, j)


    def test__update_from_dict(self):
        foo = get_model('Foo')()

        foo.update_from_dict({'s': 'bob'})
        self.assertEqual(
            foo.to_json(),
            {'s': 'bob'},
        )

        foo.update_from_dict({'s': 'abc', 'i': 12})
        self.assertEqual(
            foo.to_json(),
            {'s': 'abc', 'i': 12},
        )

        foo.update_from_dict({})
        self.assertEqual(
            foo.to_json(),
            {'s': 'abc', 'i': 12},
        )

        foo.update_from_dict({'i': None})
        self.assertEqual(
            foo.to_json(),
            {'s': 'abc'},
        )

        foo.update_from_dict({'s': None, 'i': 32}, ignore_none=True)
        self.assertEqual(
            foo.to_json(),
            {'s': 'abc', 'i': 32},
        )

        foo.update_from_dict({'s': None})
        self.assertEqual(
            foo.to_json(),
            {'i': 32},
        )
