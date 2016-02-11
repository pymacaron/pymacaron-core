from datetime import date
import pprint
import yaml
from klue.swagger.spec import ApiSpec


def test_apispec_constructor():
    yaml_str = """
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
"""
    swagger_dict = yaml.load(yaml_str)
    spec = ApiSpec(swagger_dict)
    assert spec.host == 'pnt-login.elasticbeanstalk.com'
    assert spec.port == 80
    assert spec.protocol == 'http'
    assert spec.version == '0.0.1'

    yaml_str = """
swagger: '2.0'
info:
  title: test
  version: '1.2.3'
  description: Just a test
host: pnt-login.elasticbeanstalk.com
schemes:
  - https
basePath: /v1
produces:
  - application/json
"""
    swagger_dict = yaml.load(yaml_str)
    spec = ApiSpec(swagger_dict)
    assert spec.host == 'pnt-login.elasticbeanstalk.com'
    assert spec.port == 443
    assert spec.protocol == 'https'
    assert spec.version == '1.2.3'


def test_apispec_constructor_https_default():
    yaml_str = """
swagger: '2.0'
info:
  title: test
  version: '0.0.1'
  description: Just a test
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
  - https
basePath: /v1
produces:
  - application/json
"""
    swagger_dict = yaml.load(yaml_str)
    spec = ApiSpec(swagger_dict)
    assert spec.host == 'pnt-login.elasticbeanstalk.com'
    assert spec.port == 443
    assert spec.protocol == 'https'
    assert spec.version == '0.0.1'


def test_call_on_each_endpoint_invalid_produces():

    def foo():
        pass

    yaml_str = """
swagger: '2.0'
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
  - https
paths:
  /v1/auth/login:
    post:
      parameters:
        - in: query
          name: whatever
          description: User login credentials.
          required: true
          type: string
      x-bind-server: pnt_login.handlers.do_login
"""
    swagger_dict = yaml.load(yaml_str)
    spec = ApiSpec(swagger_dict)
    try:
        spec.call_on_each_endpoint(foo)
    except Exception as e:
        print("error: " + str(e))
        assert "Swagger api has no 'produces' section" in str(e)
    else:
        assert 0

    yaml_str = """
swagger: '2.0'
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
  - https
paths:
  /v1/auth/login:
    post:
      parameters:
        - in: query
          name: whatever
          description: User login credentials.
          required: true
          type: string
      produces:
        - foo/bar
      x-bind-server: pnt_login.handlers.do_login
"""
    swagger_dict = yaml.load(yaml_str)
    spec = ApiSpec(swagger_dict)
    try:
        spec.call_on_each_endpoint(foo)
    except Exception as e:
        assert "Only 'application/json' is supported" in str(e)
    else:
        assert 0

    yaml_str = """
swagger: '2.0'
host: pnt-login.elasticbeanstalk.com
schemes:
  - http
  - https
paths:
  /v1/auth/login:
    post:
      parameters:
        - in: query
          name: whatever
          description: User login credentials.
          required: true
          type: string
      produces:
        - foo/bar
        - bar/baz
      x-bind-server: pnt_login.handlers.do_login
"""
    swagger_dict = yaml.load(yaml_str)
    spec = ApiSpec(swagger_dict)
    try:
        spec.call_on_each_endpoint(foo)
    except Exception as e:
        assert "Expecting only one type" in str(e)
    else:
        assert 0


call_count = 0

def test_call_on_each_endpoint():

    yaml_str = """
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
paths:
  /v1/auth/login:
    post:
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
      x-bind-server: pnt_login.handlers.do_login
      x-bind-client: login
      x-auth-required: false
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'

  /v1/auth/logout/:
    get:
      summary: blabla
      description: blabla
      parameters:
        - in: query
          name: baboom
          description: foooo
          required: true
          type: string
      produces:
        - application/json
      x-bind-server: pnt_login.babar
      x-decorate-request: foo.bar.baz
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'

  /v1/version/:
    get:
      summary: blabla
      description: blabla
      produces:
        - application/json
      x-bind-server: do_version
      x-decorate-server: foo.bar.baz
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'

  /v1/ignoreme/:
    get:
      summary: blabla
      description: blabla
      produces:
        - application/json
      x-no-bind-server: true
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'

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
      password_hash:
        type: string
        description: MD5 of user''s password, truncated to 16 first hexadecimal characters.
"""

    swagger_dict = yaml.load(yaml_str)
    spec = ApiSpec(swagger_dict)

    def test_callback(data):
        print("Looking at %s %s" % (data.method, data.path))

        global call_count
        call_count = call_count + 1

        assert type(data.operation).__name__ == 'Operation'

        if data.path == '/v1/auth/logout/':
            assert data.method == 'GET'
            assert data.handler_server == 'pnt_login.babar'
            assert data.handler_client is None
            assert data.decorate_server is None
            assert data.decorate_request == 'foo.bar.baz'
            assert data.param_in_body is False
            assert data.param_in_query is True
            assert data.no_params is False

        elif data.path == '/v1/auth/login':
            assert data.method == 'POST'
            assert data.handler_server == 'pnt_login.handlers.do_login'
            assert data.handler_client == 'login'
            assert data.decorate_server is None
            assert data.decorate_request is None
            assert data.param_in_body is True
            assert data.param_in_query is False
            assert data.no_params is False

        elif data.path == '/v1/version':
            assert data.method == 'GET'
            assert data.handler_server == 'do_version'
            assert data.handler_client is None
            assert data.decorate_request is None
            assert data.decorate_server == 'foo.bar.baz'
            assert data.param_in_body is False
            assert data.param_in_query is False
            assert data.no_params is True

    spec.call_on_each_endpoint(test_callback)

    assert call_count == 3


def test_model_to_json():
    # Test model_to_json on a deep structure, with object in object

    yaml_str = """
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

  Foo:
    type: object
    description: Foo
    properties:
      token:
        type: string
        description: Session token.
      bar:
        $ref: '#/definitions/Bar'

  Bar:
    type: object
    description: Bar
    properties:
      a:
        type: string
        description: a
      b:
        type: string
        format: date-time
        description: b
"""

    swagger_dict = yaml.load(yaml_str)
    spec = ApiSpec(swagger_dict)

    Foo = spec.definitions['Foo']
    Bar = spec.definitions['Bar']

    f = Foo(
        token='abcd',
        bar=Bar(
            a='1',
            b=date.today()
        )
    )

    print("foo: " + pprint.pformat(f))

    j = spec.model_to_json(f)
    assert j['bar']['a'] == '1'
