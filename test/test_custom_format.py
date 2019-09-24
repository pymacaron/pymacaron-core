import unittest
from jsonschema.exceptions import ValidationError
from bravado_core.formatter import SwaggerFormat
from bravado_core.exception import SwaggerValidationError
from bravado_core.unmarshal import unmarshal_model
from bravado_core.validate import validate_object
from pymacaron_core.swagger.api import API

formats = []

#
# Stripe Card Token
#

def validate_foo(foo):
    if foo != 'foo':
        raise SwaggerValidationError("Foo is not foo")


foo_format = SwaggerFormat(
    format='foo',
    to_wire=lambda s: s,
    to_python=lambda s: s,
    validate=validate_foo,
    description='a foo'
)

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

    def test_custom_format(self):
        api = API('somename', yaml_str=yaml_str, formats=[foo_format])

        self.assertTrue(hasattr(api.model, 'Foo'))

        # marshal and unmarshal
        f = api.model.Foo(foo='123')
        j = api.api_spec.model_to_json(f)
        self.assertDictEqual(j, {'foo': '123'})

        model_def = api.api_spec.swagger_dict['definitions']['Foo']
        f = unmarshal_model(api.api_spec.spec, model_def, j)
        self.assertEqual(f.foo, '123')

        # validate
        validate_object(api.api_spec.spec, model_def, {'foo': 'foo'})

        try:
            validate_object(api.api_spec.spec, model_def, {'foo': '123'})
        except ValidationError as e:
            self.assertTrue("'123' is not a 'foo'" in str(e))
        else:
            assert 0
