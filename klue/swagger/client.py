import grequests
import pprint
import jsonschema
import logging
import flask
from klue.exceptions import KlueException, ValidationError
from klue.utils import get_function
from bravado_core.response import unmarshal_response, OutgoingResponse


log = logging.getLogger(__name__)


try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack


def generate_client_callers(spec, timeout, error_callback):
    """Return a dict mapping method names to anonymous functions that
    will call the server's endpoint of the corresponding name as
    described in the api defined by the swagger dict and bravado spec"""

    callers_dict = {}

    def mycallback(endpoint):
        if not endpoint.handler_client:
            return

        log.info("Generating client for %s %s" % (endpoint.method, endpoint.path))

        callers_dict[endpoint.handler_client] = _generate_client_caller(spec, endpoint, timeout, error_callback)

    spec.call_on_each_endpoint(mycallback)

    return callers_dict



def _generate_client_caller(spec, endpoint, timeout, error_callback):

    url = "%s://%s:%s/%s" % (spec.protocol,
                             spec.host,
                             spec.port,
                             endpoint.path)

    decorator = None
    if endpoint.decorate_request:
        decorator = get_function(endpoint.decorate_request)

    method = endpoint.method.lower()
    if method not in ('get', 'post'):
        return error_callback(KlueException("BUG: method %s for %s is not supported. Only get and post are." %
                                            (endpoint.method, endpoint.path)))

    grequests_method = getattr(grequests, method)
    if decorator:
        grequests_method = decorator(grequests_method)
    import pprint

    def client(*args, **kwargs):
        """Call the server endpoint and handle marshaling/unmarshaling of parameters/result.

        client takes either a dict of query parameters, or an object representing the unique
        body parameter.
        """

        headers = {}
        data = None
        params = None

        custom_url = url

        if hasattr(stack.top, 'call_id'):
            headers['KlueCallID'] = stack.top.call_id
        if hasattr(stack.top, 'call_path'):
            headers['KlueCallPath'] = stack.top.call_path

        if endpoint.param_in_query:
            # The query parameters are contained in **kwargs
            params = kwargs
            # TODO: validate params? or let the server do that...
        elif endpoint.param_in_body:
            # The body parameter is the first elem in *args
            if len(args) != 1:
                return error_callback(ValidationError("%s expects exactly 1 parameter" % endpoint.handler_client))
            data = spec.model_to_json(args[0])
        elif endpoint.param_in_path:
            # Client expects arguments as a dict, not as a list
            assert len(args) == 0
            print("got url and params: " + pprint.pformat([url, kwargs]))
            custom_url = _format_flask_url(url, kwargs)

        # TODO: if request times-out, retry a few times, else return KlueTimeOutError
        # Call the right grequests method (get, post...)
        greq = grequests_method(custom_url,
                                data=data,
                                params=params,
                                headers=headers,
                                timeout=timeout)

        return ClientCaller(greq, endpoint.operation, endpoint.method, endpoint.path, error_callback)

    return client


def _format_flask_url(url, params):
    # TODO: make this code more robust: error if some params are left unmatched
    # or if url still contains placeholders after replacing
    for name, value in params.iteritems():
        url = url.replace("<%s>" % name, str(value))
    return url


class ClientCaller():

    def __init__(self, greq, operation, method, path, error_callback):
        self.operation = operation
        self.greq = greq
        self.method = method
        self.path = path
        self.error_callback = error_callback

    def call(self):
        # TODO: add retry handler to map
        log.info("Calling %s %s" % (self.method, self.path))
        responses = grequests.map([self.greq])
        assert len(responses) == 1
        response = responses[0]

        # If the remote-server returned an error, raise it as a local KlueException
        if str(response.status_code) != '200':
            log.warn("Call to %s %s returns error: %s" % (self.method, self.path, response.text))
            if 'error_description' in response.text:
                # We got a KlueException: unmarshal it and return as valid return value
                # UGLY FRAGILE CODE. To be replaced by proper exception scheme
                pass
            else:
                # Unknown exception...
                k = KlueException(response.text)
                k.status_code = response.status_code
                return self.error_callback(k)

        result = self._unmarshal(response)
        log.info("Call to %s %s returned an instance of %s" % (self.method, self.path, type(result)))
        return result

    def _unmarshal(self, response):
        # Now transform the request's Response object into an instance of a
        # swagger model
        try:
            result = unmarshal_response(response, self.operation)
        except jsonschema.exceptions.ValidationError as e:
            k = ValidationError(str(e))
            k.status_code = 500
            return self.error_callback(k)
        return result

def async_call(*client_callers):
    """Call these server endpoints asynchronously and return Model or Error objects"""
    # TODO: add retry handler to map
    responses = grequests.map(client_callers)
    results = []
    for i in xrange(1, len(responses)):
        client_caller = client_callers[i]
        response = responses[i]
        results.append(client_caller._unmarshal(response))
