import pprint
from pymacaron_core.swagger.api import API


class Handlers():
    pass


yaml_str = """
swagger: '2.0'
info:
  version: '0.0.1'
host: some.server.com
schemes:
  - http
produces:
  - application/json
paths:
  /v1/some/path:
    get:
      summary: blabla
      description: blabla
      parameters:
        - in: query
          name: arg1
          description: foooo
          required: true
          type: string
        - in: query
          name: arg2
          description: foooo
          required: true
          type: string
      produces:
        - application/json
      x-bind-server: pnt_common.test.default_timeout
      x-bind-client: do_test
      x-auth-required: false
      responses:
        '200':
          description: result
          schema:
            $ref: '#/definitions/Result'

  /v1/some/more/path:
    get:
      description: blabla
      produces:
        - application/json
      x-bind-server: pnt_common.test.default_timeout
      x-bind-client: do_more_test
      responses:
        '200':
          description: result
          schema:
            $ref: '#/definitions/Result'

definitions:

  Result:
    type: object
    description: result
    properties:
      foo:
        type: string
        description: blabla
      bar:
        type: string
        description: bloblo

  Param:
    type: object
    description: param
    properties:
      arg1:
        type: string
        description: blabla
      arg2:
        type: string
        description: bloblo

  Error:
    type: object
    description: param
    properties:
      code:
        type: string
        description: blabla
      message:
        type: string
        description: bloblo

"""


def test_api_constructor():
    api = API('somename', yaml_str=yaml_str)
    assert api.name == 'somename'
    assert api.api_spec
    assert api.client_timeout == 10
    assert api.error_callback
    assert not api.is_server


def test_api_models():
    api = API('somename', yaml_str=yaml_str)

    # Check that the models work
    assert hasattr(api.model, 'Param')
    assert hasattr(api.model, 'Result')
    assert hasattr(api.model, 'Error')

    name_to_model = {
        'Param': api.model.Param,
        'Result': api.model.Result,
        'Error': api.model.Error,
    }
    for name, model in list(name_to_model.items()):
        i = model()
        type_name = type(i).__name__
        print("type: %s = " % name + pprint.pformat(type(api.model.Param()).__name__))
        assert type_name == name

    P = api.model.Param(arg1='1')
    print("p: " + pprint.pformat(P))
    assert type(P).__name__ == 'Param'
    assert P.arg1 == '1'


def test_api_get_version():
    api = API('somename', yaml_str=yaml_str)
    assert api.get_version() == '0.0.1'


def test_api_clients():
    api = API('somename', yaml_str=yaml_str)
    assert hasattr(api.client, 'do_test')
    assert hasattr(api.client, 'do_more_test')
    assert api.client.do_test != api.client.do_more_test
