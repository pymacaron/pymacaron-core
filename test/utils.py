import pprint
import unittest
import yaml
from klue.swagger.spec import ApiSpec
from klue.swagger.api import default_error_callback
from klue.swagger.client import generate_client_callers


class KlueClientTest(unittest.TestCase):

    def generate_client_and_spec(self, yaml_str, callback=default_error_callback):

        swagger_dict = yaml.load(yaml_str)
        spec = ApiSpec(swagger_dict)
        callers_dict = generate_client_callers(
            spec,
            10,
            callback,
        )

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
