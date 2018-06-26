import jsonschema
import logging
import uuid
from functools import wraps
from werkzeug.exceptions import BadRequest
from flask import request, jsonify
from flask_cors import cross_origin
from pymacaron_core.exceptions import PyMacaronCoreException, ValidationError, add_error_handlers
from pymacaron_core.utils import get_function
from bravado_core.request import IncomingRequest, unmarshal_request


log = logging.getLogger(__name__)


try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack


def spawn_server_api(api_name, app, api_spec, error_callback, decorator):
    """Take a a Flask app and a swagger file in YAML format describing a REST
    API, and populate the app with routes handling all the paths and methods
    declared in the swagger file.

    Also handle marshaling and unmarshaling between json and object instances
    representing the definitions from the swagger file.
    """

    def mycallback(endpoint):
        handler_func = get_function(endpoint.handler_server)

        # Generate api endpoint around that handler
        handler_wrapper = _generate_handler_wrapper(api_name, api_spec, endpoint, handler_func, error_callback, decorator)

        # Bind handler to the API path
        log.info("Binding %s %s ==> %s" % (endpoint.method, endpoint.path, endpoint.handler_server))
        endpoint_name = '_'.join([endpoint.method, endpoint.path]).replace('/', '_')
        app.add_url_rule(endpoint.path, endpoint_name, handler_wrapper, methods=[endpoint.method])


    api_spec.call_on_each_endpoint(mycallback)

    # Add custom error handlers to the app
    add_error_handlers(app)


def _responsify(api_spec, error, status):
    """Take a bravado-core model representing an error, and return a Flask Response
    with the given error code and error instance as body"""
    result_json = api_spec.model_to_json(error)
    r = jsonify(result_json)
    r.status_code = status
    return r


def _generate_handler_wrapper(api_name, api_spec, endpoint, handler_func, error_callback, global_decorator):
    """Generate a handler method for the given url method+path and operation"""

    # Decorate the handler function, if Swagger spec tells us to
    if endpoint.decorate_server:
        endpoint_decorator = get_function(endpoint.decorate_server)
        handler_func = endpoint_decorator(handler_func)

    @wraps(handler_func)
    def handler_wrapper(**path_params):
        log.info(" ")
        log.info(" ")
        log.info("=> INCOMING REQUEST %s %s -> %s" %
                 (endpoint.method, endpoint.path, handler_func.__name__))
        log.info(" ")
        log.info(" ")

        # Get caller's pym-call-id or generate one
        call_id = request.headers.get('PymCallID', None)
        if not call_id:
            call_id = str(uuid.uuid4())
        stack.top.call_id = call_id

        # Append current server to call path, or start one
        call_path = request.headers.get('PymCallPath', None)
        if call_path:
            call_path = "%s.%s" % (call_path, api_name)
        else:
            call_path = api_name
        stack.top.call_path = call_path

        if endpoint.param_in_body or endpoint.param_in_query:
            # Turn the flask request into something bravado-core can process...
            try:
                req = FlaskRequestProxy(request, endpoint.param_in_body)
            except BadRequest:
                ee = error_callback(ValidationError("Cannot parse json data: have you set 'Content-Type' to 'application/json'?"))
                return _responsify(api_spec, ee, 400)

            try:
                # Note: unmarshall validates parameters but does not fail
                # if extra unknown parameters are submitted
                parameters = unmarshal_request(req, endpoint.operation)
                # Example of parameters: {'body': RegisterCredentials()}
            except jsonschema.exceptions.ValidationError as e:
                ee = error_callback(ValidationError(str(e)))
                return _responsify(api_spec, ee, 400)

        # Call the endpoint, with proper parameters depending on whether
        # parameters are in body, query or url
        args = []
        kwargs = {}

        if endpoint.param_in_path:
            kwargs = path_params

        if endpoint.param_in_body:
            # Remove the parameters already defined in path_params
            for k in list(path_params.keys()):
                del parameters[k]
            lst = list(parameters.values())
            assert len(lst) == 1
            args.append(lst[0])

        if endpoint.param_in_query:
            kwargs.update(parameters)

        result = handler_func(*args, **kwargs)

        if not result:
            e = error_callback(PyMacaronCoreException("Have nothing to send in response"))
            return _responsify(api_spec, e, 500)

        # Did we get the expected response?
        if endpoint.produces_html:
            if type(result) is not tuple:
                e = error_callback(PyMacaronCoreException("Method %s should return %s but returned %s" %
                                                          (endpoint.handler_server, endpoint.produces, type(result))))
                return _responsify(api_spec, e, 500)

            # Return an html page
            return result

        elif endpoint.produces_json:
            if not hasattr(result, '__module__') or not hasattr(result, '__class__'):
                e = error_callback(PyMacaronCoreException("Method %s did not return a class instance but a %s" %
                                                          (endpoint.handler_server, type(result))))
                return _responsify(api_spec, e, 500)

            # If it's already a flask Response, just pass it through.
            # Errors in particular may be either passed back as flask Responses, or
            # raised as exceptions to be caught and formatted by the error_callback
            result_type = result.__module__ + "." + result.__class__.__name__
            if result_type == 'flask.wrappers.Response':
                return result

            # We may have got a pymacaron Error instance, in which case
            # it has a http_reply() method...
            if hasattr(result, 'http_reply'):
                # Let's transform this Error into a flask Response
                log.info("Looks like a pymacaron error instance - calling .http_reply()")
                return result.http_reply()

            # Otherwise, assume no error occured and make a flask Response out of
            # the result.

            # TODO: check that result is an instance of a model expected as response from this endpoint
            result_json = api_spec.model_to_json(result)

            # Send a Flask Response with code 200 and result_json
            r = jsonify(result_json)
            r.status_code = 200
            return r

    handler_wrapper = cross_origin(headers=['Content-Type', 'Authorization'])(handler_wrapper)

    # And encapsulate all in a global decorator, if given one
    if global_decorator:
        handler_wrapper = global_decorator(handler_wrapper)

    return handler_wrapper


class FlaskRequestProxy(IncomingRequest):
    """Take a flask.request object and make it look like a
    bravado_core.request.IncomingRequest"""

    path = None
    query = None
    form = None
    headers = None
    files = None
    _json = None

    def __init__(self, request, has_json):
        self.request = request
        self.query = request.args
        self.path = request.view_args
        self.headers = request.headers
        if has_json:
            self._json = self.request.get_json(force=True)

    def json(self):
        # Convert a weltkreuz ImmutableDict to a simple python dict
        return self._json
