import unittest
import yaml
from flask import Flask
from pymacaron_core.swagger.spec import ApiSpec
from pymacaron_core.swagger.api import default_error_callback
from pymacaron_core.swagger.client import generate_client_callers
from pymacaron_core.swagger.server import spawn_server_api


class PymTest(unittest.TestCase):

    def generate_client_and_spec(self, yaml_str, callback=default_error_callback, local=False):

        swagger_dict = yaml.load(yaml_str, Loader=yaml.FullLoader)
        spec = ApiSpec(swagger_dict)
        spec.load_models()
        callers_dict = generate_client_callers(
            spec,
            10,
            callback,
            local,
            None
        )

        assert len(list(callers_dict.keys())) == 1
        assert 'do_test' in callers_dict

        handler = callers_dict['do_test']
        assert type(handler).__name__ == 'function'

        return handler, spec


    def generate_server_app(self, yaml_str, callback=default_error_callback):
        swagger_dict = yaml.load(yaml_str, Loader=yaml.FullLoader)
        spec = ApiSpec(swagger_dict)
        spec.load_models()
        app = Flask('test')
        spawn_server_api('somename', app, spec, callback, None)
        return app, spec



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
        - in: path
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


    yaml_path_query_param = """
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
  /v1/some/{foo}/path:
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

    yaml_path_body_param = """
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
  /v1/some/{foo}/path:
    get:
      summary: blabla
      description: blabla
      parameters:
        - in: path
          name: foo
          description: foooo
          required: true
          type: string
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

    yaml_no_param = yaml_base + """
paths:
  /v1/no/param:
    get:
      summary: blabla
      description: blabla
      produces:
        - application/json
      x-bind-server: pymacaron_core.test.return_token
      x-auth-required: false
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'
"""

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
      x-bind-server: pymacaron_core.test.return_token
      x-auth-required: false
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'
"""

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
      x-bind-server: pymacaron_core.test.return_token
      x-auth-required: false
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'
"""

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
      x-bind-server: pymacaron_core.test.return_token
      x-auth-required: false
      responses:
        200:
          description: A session token
          schema:
            $ref: '#/definitions/SessionToken'
"""
