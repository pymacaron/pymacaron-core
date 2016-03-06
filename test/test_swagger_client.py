import pprint
import yaml
import responses
from httplib import HTTPResponse
from mock import patch, MagicMock
from klue.swagger.api import default_error_callback
from klue.swagger.spec import ApiSpec
from klue.swagger.client import generate_client_callers, _format_flask_url
from klue.exceptions import KlueException, ValidationError

def _slurp_yaml(yaml_str):
    swagger_dict = yaml.load(yaml_str)
    spec = ApiSpec(swagger_dict)
    callers_dict = generate_client_callers(spec, 10, default_error_callback)

    assert len(callers_dict.keys()) == 1
    assert 'do_test' in callers_dict

    handler = callers_dict['do_test']
    assert type(handler).__name__ == 'function'

    return handler, spec


yaml_query_param = """
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
      x-bind-server: whatever
      x-bind-client: do_test
      x-auth-required: false
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
"""

@responses.activate
def test_client_with_query_param():
    handler, _ = _slurp_yaml(yaml_query_param)

    responses.add(responses.GET, "http://some.server.com:80//v1/some/path",
                  body='{"foo": "a", "bar": "b"}', status=200,
                  content_type="application/json")

    res = handler(arg1='this', arg2='that').call()

    print("response: " + pprint.pformat(res))
    assert type(res).__name__ == 'Result'
    assert res.foo == 'a'
    assert res.bar == 'b'


@patch('klue.swagger.client.grequests')
def test_requests_parameters_with_query_param(grequests):
    grequests.get = MagicMock()
    handler, _ = _slurp_yaml(yaml_query_param)
    try:
        handler(arg1='this', arg2='that').call()
    except Exception as e:
        pass

    grequests.get.assert_called_once_with('http://some.server.com:80//v1/some/path',
                                          data=None,
                                          headers={'Content-Type': 'application/json'},
                                          params={'arg1': 'this', 'arg2': 'that'},
                                          timeout=(10, 10))


yaml_body_param = """
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
  /v1/some/path:
    post:
      summary: blabla
      description: blabla
      parameters:
        - in: body
          name: arg1
          description: foooo
          required: true
          schema:
            $ref: '#/definitions/Param'
      produces:
        - application/json
      x-bind-server: whatever
      x-bind-client: do_test
      x-auth-required: false
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

"""

@responses.activate
def test_client_with_body_param():
    handler, spec = _slurp_yaml(yaml_body_param)

    responses.add(responses.POST, "http://some.server.com:80//v1/some/path",
                  body='{"foo": "a", "bar": "b"}', status=200,
                  content_type="application/json")

    # Only 1 parameter expected
    try:
        res = handler()
    except ValidationError as e:
        assert 1
    else:
        assert 0
    try:
        res = handler(1, 2)
    except ValidationError as e:
        assert 1
    else:
        assert 0

    # Send a valid parameter object
    model_class = spec.definitions['Param']
    param = model_class(arg1='a', arg2='b')

    res = handler(param).call()
    assert type(res).__name__ == 'Result'
    assert res.foo == 'a'
    assert res.bar == 'b'


@patch('klue.swagger.client.grequests')
def test_requests_parameters_with_body_param(grequests):
    handler, spec = _slurp_yaml(yaml_body_param)
    model_class = spec.definitions['Param']
    param = model_class(arg1='a', arg2='b')

    try:
        handler(param).call()
    except Exception as e:
        pass

    grequests.post.assert_called_once_with('http://some.server.com:80//v1/some/path',
                                           data='{"arg1": "a", "arg2": "b"}',
                                           headers={'Content-Type': 'application/json'},
                                           params=None,
                                           timeout=(10, 10))


def test_client_with_auth_required():
    pass


def test__format_flask_url():
    u = _format_flask_url(
        "/v1/seller/<item_id>/<path>/foo",
        {
            'item_id': '1234',
            'path': 'abcd',
        }
    )
    assert u == "/v1/seller/1234/abcd/foo"

    u = _format_flask_url(
        "/v1/seller/<item_id>/<path>/foo/<item_id>",
        {
            'item_id': 1234,
            'path': 'abcd',
        }
    )
    assert u == "/v1/seller/1234/abcd/foo/1234"


yaml_path_param = """
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
  /v1/some/{foo}/path/{bar}:
    get:
      summary: blabla
      description: blabla
      parameters:
        - in: path
          name: foo
          description: foooo
          required: true
          type: string
        - in: query
          name: bar
          description: baaar
          required: true
          type: string
      produces:
        - application/json
      x-bind-server: whatever
      x-bind-client: do_test
      x-auth-required: false
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
"""

@responses.activate
def test_client_with_path_param():
    handler, spec = _slurp_yaml(yaml_path_param)

    responses.add(responses.GET,
                  "http://some.server.com:80//v1/some/123/path/456",
                  body='{"foo": "a", "bar": "b"}',
                  status=200,
                  content_type="application/json")

    # Make a valid call
    res = handler(foo=123, bar=456).call()
    assert type(res).__name__ == 'Result'
    assert res.foo == 'a'
    assert res.bar == 'b'


@patch('klue.swagger.client.grequests')
def test_requests_parameters_with_path_params(grequests):
    handler, spec = _slurp_yaml(yaml_path_param)

    try:
        handler(foo=123, bar=456).call()
    except Exception as e:
        pass

    grequests.get.assert_called_once_with(
        'http://some.server.com:80//v1/some/123/path/456',
        data=None,
        headers={'Content-Type': 'application/json'},
        params=None,
        timeout=(10, 10))


@patch('klue.swagger.client.grequests')
def test_handler_extra_parameters(grequests):
    handler, spec = _slurp_yaml(yaml_path_param)

    try:
        handler(
            foo=123,
            bar=456,
            max_attempts=2,
            read_timeout=6,
            connect_timeout=8
        ).call()
    except Exception as e:
        pass

    grequests.get.assert_called_once_with(
        'http://some.server.com:80//v1/some/123/path/456',
        data=None,
        headers={'Content-Type': 'application/json'},
        params=None,
        timeout=(8, 6))

# TODO: test max_attempts?
