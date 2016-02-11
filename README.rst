Klue Client-Server
==================

Dynamically generate client libraries and Flask servers based on Swagger
specifications of REST apis.

Purpose
-------

A typical micro-service will expose a REST API on its server side, while making
client calls to a number of other services nearby.

Given a set of Swagger specifications describing the APIs of these services,
Klue Client-Server will populate a Flask app with auto-generated server
endpoints for all specified routes, as well as generate client libraries for
every client API. Both client and server stubs handle marshaling/unmarshaling
of json documents to and from objects modeled upon the Swagger definitions for
each API, as well as provide format verifications of these objects.

Klue Client-Server relies on bravado-core for marshaling/unmarshaling and
format validation.

The generated client library support both synchronous and asynchronous/parallel
calls using grequests.

Disclaimer
----------

Klue Client-Server is under active development. Its API is subject to
change. It has been tested only on python 2.7.

Usage
-----

First, load the Swagger specifications of all the services your server will use:

.. code-block:: python

    from klue.swagger import ApiPool

    ApiPool.add('public', yaml_path='public.yaml')
    ApiPool.add('login', yaml_path='login.yaml')
    ApiPool.add('user', yaml_path='user.yaml', timeout=20)


Usage - Generating Server
=========================

In the Swagger spec describing the server side, each endpoint that you want to
have auto-generated into the Flask app should have the 'x-bind-server'
attribute set to the path of a python method that will take as argument an
object modelled on the endpoint's argument, and return an object matching that
of the endpoint's reponses (See bravado-core for details):

.. code-block:: yaml

    /login:
      post:
        summary: Login a user.
        produces:
          - application/json
        x-bind-server: myserver.handlers.do_login
        parameters:
          - in: body
            name: body
            description: User login credentials.
            required: true
            schema:
              $ref: "#/definitions/Credentials"
        responses:
          200:
            description: API version
            schema:
              $ref: '#/definitions/Welcome'
          default:
            description: Error
            schema:
              $ref: '#/definitions/Error'


Populate a Flask app with server endpoints for the 'login' api:

.. code-block:: python

    app = Flask(__name__)
    ApiPool.login.spawn_api(app)


Implement the 'do_login' endpoint:

.. code-block:: python

    from flask import jsonify
    from klue.swagger import ApiPool
    from klue.exceptions import KlueExeption

    def do_login(credentials):
        if authenticate_user(credentials):
            # Get the class representing bravado-core Welcome objects
            Welcome = ApiPool.login.model.Welcome
            # Instantiate Welcome and return it
            return Welcome(message="Welcome!")
        else:
            # Rise an error in the API's error format, directly as
            # a Flask response object
            r = jsonify({'error': 'INVALID_CREDENTIALS'})
            r.status_code = 401
            return r


Usage - Generating Client
=========================

In the Swagger spec describing the server you want to call, each endpoint that
you want to have auto-generated into the client library should have the
'x-bind-client' attribute set to the path of a python method that will take as
argument an object modelled on the endpoint's argument, and return an object
matching that of the endpoint's reponses (See bravado-core for details):

.. code-block:: yaml

    /version:
      get:
        summary: Return the API''s version.
        produces:
          - application/json
        x-bind-client: version
        responses:
          200:
            description: API version
            schema:
              $ref: '#/definitions/Version'

Calling that server now looks like (assuming the server api is called 'public'):

.. code-block:: python

    from klue.swagger import ApiPool

    # Call the /version endpoint on the host:port specified in the Swagger
    # spec, and return a Version object:
    version = ApiPool.public.client.version().call()

To call multiple server endpoints in parallel:

.. code-block:: python

    from klue.swagger import ApiPool
    from klue.swagger.client import async_call

    # Call two endpoints in parallel:
    [result_version, result_login]
        = async_call(
             ApiPool.public.client.version(),
             ApiPool.login.client.login(credentials),
        )

Install
-------

.. code-block:: shell

    pip install -i https://testpypi.python.org/pypi klue-client-server