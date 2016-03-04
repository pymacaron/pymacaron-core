import pprint
import yaml
import json
from flask import Flask, request, jsonify
from klue.swagger.spec import ApiSpec
from klue.swagger.server import spawn_server_api
from klue.swagger.api import default_error_callback
from klue.exceptions import KlueException
from mock import patch


#
# A base swagger YAML file
#

yaml_base = """
swagger: '2.0'
info:
  title: test
  version: '0.0.1'
  description: Just a test
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
basePath: /v1
produces:
  - application/json
definitions:
  SessionToken:
    type: object
    description: An authenticated user''s session token
    properties:
      token:
        type: string
        description: Session token.
  Credentials:
    type: object
    description: A user''s login credentials.
    properties:
      email:
        type: string
        description: User''s email.
      int:
        type: string
        description: MD5 of user''s password, truncated to 16 first hexadecimal characters.
    required:
      - email
"""

def gen_app(ystr):
    swagger_dict = yaml.load(ystr)
    spec = ApiSpec(swagger_dict)
    app = Flask('test')
    spawn_server_api('somename', app, spec, default_error_callback, None)
    return app, spec

def assert_ok_reply(r, token):
    assert r.status_code == 200, r.status_code
    j = json.loads(r.data.decode("utf-8"))
    print("json reply: " + pprint.pformat(j))
    assert j['token'] == token

def assert_error(r, status, content):
    assert str(r.status_code) == str(status), "status [%s] == [%s]" % (r.status_code, status)
    assert content in r.status, "[%s] in [%s]" % (content, r.status)

#
# TESTS
#

yaml_no_param = yaml_base + """
paths:
  /v1/no/param:
    get:
      summary: blabla
      description: blabla
      produces:
        - application/json
      x-bind-server: klue.test.return_token
      x-auth-required: false
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'
"""


@patch('klue.test.return_token')
def test_swagger_server_no_param(func):
    app, spec = gen_app(yaml_no_param)

    func.__name__ = 'return_token'
    SessionToken = spec.definitions['SessionToken']
    func.return_value = SessionToken(token='123')

    with app.test_client() as c:
        r = c.get('/v1/no/param')
        assert_ok_reply(r, '123')
        func.assert_called_once_with()


@patch('klue.test.return_token')
def test_swagger_server_no_result(func):
    app, spec = gen_app(yaml_no_param)

    func.__name__ = 'return_token'
    func.return_value = None

    with app.test_client() as c:
        r = c.get('/v1/no/param')
        assert_error(r, 500, 'INTERNAL SERVER ERROR')


@patch('klue.test.return_token')
def test_swagger_server_pass_through_responses(func):
    app, spec = gen_app(yaml_no_param)

    with app.test_request_context('/'):

        func.__name__ = 'return_token'
        r = jsonify({'foo': 'bar'})
        r.status_code = 534
        func.return_value = r

        with app.test_client() as c:
            r = c.get('/v1/no/param')
            print("sc: %s" % str(r.status_code))
            assert r.status_code == 534, r.status_code
            j = json.loads(r.data.decode("utf-8"))
            print("json reply: " + pprint.pformat(j))
            assert j['foo'] == 'bar'


@patch('klue.test.return_token')
def test_swagger_invalid_server_return_value(func):
    app, spec = gen_app(yaml_no_param)

    func.__name__ = 'return_token'
    func.return_value = {'a': 1}

    with app.test_client() as c:
        r = c.get('/v1/no/param')
        assert_error(r, 500, 'INTERNAL SERVER ERROR')
#         try:
#             c.get('/v1/no/param')
#         except Exception as e:
#             print("GOT EXCEPT %s" % str(e))
#             assert_error(e, 'InternalServerError', 'Contains')
#         else:
#             assert 0

# TODO: enable this test when server-side validation is enabled
#
#    c = spec.definitions['Credentials']
#    func.return_value = c(email='asdasd')
#
#     with app.test_client() as c:
#         r = c.get('/v1/no/param')
#         print("sc: %s" % str(r.status_code))
#         assert r.status_code == 500, r.status_code
#         j = json.loads(r.data.decode("utf-8"))
#         print("json reply: " + pprint.pformat(j))
#         assert j['error'] == 'SERVER_ERROR'
#         assert 'did not return a class' in j['error_description']


yaml_in_body = yaml_base + """
paths:
  /v1/in/body:
    get:
      summary: blabla
      description: blabla
      parameters:
        - in: body
          name: whatever
          description: User login credentials.
          required: true
          schema:
            $ref: '#/definitions/Credentials'
      produces:
        - application/json
      x-bind-server: klue.test.return_token
      x-auth-required: false
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'
"""

@patch('klue.test.return_token')
def test_swagger_server_param_in_body(func):
    app, spec = gen_app(yaml_in_body)

    func.__name__ = 'return_token'
    SessionToken = spec.definitions['SessionToken']
    Credentials = spec.definitions['Credentials']
    func.return_value = SessionToken(token='456')

    with app.test_client() as c:
        r = c.get('/v1/in/body', data=json.dumps({
            'email': 'a@a.a',
            'int': '123123',
        }))
        assert_ok_reply(r, '456')
        func.assert_called_once_with(Credentials(email='a@a.a', int='123123'))


yaml_in_query = yaml_base + """
paths:
  /v1/in/query:
    get:
      summary: blabla
      description: blabla
      parameters:
        - in: query
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
      x-bind-server: klue.test.return_token
      x-auth-required: false
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'
"""

@patch('klue.test.return_token')
def test_swagger_server_param_in_query(func):
    app, spec = gen_app(yaml_in_query)

    func.__name__ = 'return_token'
    SessionToken = spec.definitions['SessionToken']
    func.return_value = SessionToken(token='456')

    with app.test_client() as c:
        r = c.get('/v1/in/query?foo=aaaa&bar=bbbb')
        assert_ok_reply(r, '456')
        func.assert_called_once_with(bar='bbbb', foo='aaaa')


@patch('klue.test.return_token')
def test_swagger_server_param_in_query__missing_required_param(func):
    app, spec = gen_app(yaml_in_query)

    func.__name__ = 'return_token'
    SessionToken = spec.definitions['SessionToken']
    func.return_value = SessionToken(token='456')

    with app.test_client() as c:
        r = c.get('/v1/in/query?bar=bbbb')
        assert_error(r, 400, 'BAD REQUEST')
        func.assert_not_called()



def test_swagger_server_auth():
    pass


@patch('klue.test.return_token')
def test_unmarshal_request_error__missing_required_argument(func):
    app, spec = gen_app(yaml_in_body)

    func.__name__ = 'return_token'
    SessionToken = spec.definitions['SessionToken']
    Credentials = spec.definitions['Credentials']
    func.return_value = SessionToken(token='456')

    with app.test_client() as c:
        r = c.get('/v1/in/body', data=json.dumps({'bazzoom': 'thiswontwork'}))
        assert_error(r, 400, 'BAD REQUEST')
        func.assert_not_called()


@patch('klue.test.return_token')
def test_unmarshal_request_error__wrong_argument_format(func):
    app, spec = gen_app(yaml_in_body)

    func.__name__ = 'return_token'
    SessionToken = spec.definitions['SessionToken']
    Credentials = spec.definitions['Credentials']
    func.return_value = SessionToken(token='456')

    with app.test_client() as c:
        data = json.dumps({
            'email': 'a@2a.a',
            'int': [1, 2, 3],
        })

        r = c.get('/v1/in/body', data=data)

        # verify server reply
# TODO: uncomment when bravado-core start returning error on this
#         assert r.status_code == 400, r.status_code
#         j = json.loads(r.data.decode("utf-8"))
#         print("json reply: " + pprint.pformat(j))
#         assert j['error'] == 'INVALID_PARAMETER'
#         assert j['status'] == 400
#         assert "email' is a required property" in j['error_description']


yaml_in_path = yaml_base + """
paths:
  /v1/in/{item}/foo/{path}:
    get:
      summary: blabla
      description: blabla
      parameters:
        - in: path
          name: item
          description: foooo
          required: true
          type: string
        - in: path
          name: path
          description: baaar
          required: true
          type: string
      produces:
        - application/json
      x-bind-server: klue.test.return_token
      x-auth-required: false
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'
"""

@patch('klue.test.return_token')
def test_swagger_server_param_in_path(func):
    app, spec = gen_app(yaml_in_path)

    func.__name__ = 'return_token'
    SessionToken = spec.definitions['SessionToken']
    func.return_value = SessionToken(token='456')

    with app.test_client() as c:
        r = c.get('/v1/in/1234/foo/bob234')
        assert_ok_reply(r, '456')
        func.assert_called_once_with(item='1234', path='bob234')


# @patch('klue.test.return_token')
# def test_swagger_server_param_in_path__missing_required_param(func):
#     app, spec = gen_app(yaml_in_query)

#     func.__name__ = 'return_token'
#     SessionToken = spec.definitions['SessionToken']
#     func.return_value = SessionToken(token='456')

#     with app.test_client() as c:
#         r = c.get('/v1/in/query?bar=bbbb')
#         assert_error(r, 400, 'BAD REQUEST')
#         func.assert_not_called()
