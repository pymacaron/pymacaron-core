from mock import MagicMock
from pymacaron_core.swagger.apipool import ApiPool
from pymacaron_core.swagger.api import API


yaml_foo = """
swagger: '2.0'
info:
  title: test
  version: '0.0.1'
  description: Just a test
host: some.server.com
schemes:
  - http
basePath: /v1
produces:
  - application/json
paths:
  /v1/foo:
    post:
      parameters:
        - in: query
          type: string
          name: arg1
          description: foooo
          required: true
      x-bind-server: pymacaron_core.test.return_token
      produces:
        - application/json
      responses:
        '200':
          description: result
          type: string
"""

yaml_bar = """
swagger: '2.0'
info:
  title: test
  version: '0.0.1'
  description: Just a test
host: another.server.com
schemes:
  - http
basePath: /v1
produces:
  - application/json
paths:
  /v1/bar:
    post:
      parameters:
        - in: query
          type: string
          name: arg1
          description: foooo
          required: true
      x-bind-server: pymacaron_core.test.return_token
      produces:
        - application/json
      responses:
        '200':
          description: result
          type: string
"""

def test_apipool_add():
    assert not hasattr(ApiPool, 'foo')
    assert not hasattr(ApiPool, 'bar')

    ApiPool().add('foo', yaml_str=yaml_foo)
    assert hasattr(ApiPool, 'foo')
    assert not hasattr(ApiPool, 'bar')
    assert isinstance(ApiPool().foo, API)

    ApiPool().add('bar', yaml_str=yaml_foo)
    assert hasattr(ApiPool, 'foo')
    assert hasattr(ApiPool, 'bar')
    assert isinstance(ApiPool().bar, API)

def test_apipool_current_server_name_api():
    assert ApiPool().current_server_name == ''
    assert ApiPool().current_server_api is None

    app = MagicMock()
    api = ApiPool().add('foo', yaml_str=yaml_foo)
    api.spawn_api(app)

    assert ApiPool().current_server_name == 'foo'
    assert ApiPool().current_server_api == api

def test__cmp_models():
    assert ApiPool._cmp_models(
        {'a': 1, 'b': 2},
        {'a': 1, 'b': 2}
    ) == 0

    assert ApiPool._cmp_models(
        {'a': 1},
        {'a': 1, 'b': 2}
    ) != 0

    assert ApiPool._cmp_models(
        {'a': 1, 'b': 2, 'x-model': 12},
        {'a': 1, 'b': 2}
    ) == 0

    assert ApiPool._cmp_models(
        {'a': 1, 'b': 2, 'x-model': 12, 'properties': {'foo': {'$ref': 'a'}}},
        {'a': 1, 'b': 2, 'properties': {'foo': {'$ref': 'a', 'x-scope': [1, 2]}}},
    ) == 0
