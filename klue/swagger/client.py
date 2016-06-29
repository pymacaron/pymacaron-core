import grequests
import pprint
import jsonschema
import json
import logging
import flask
from requests.exceptions import ReadTimeout, ConnectTimeout
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
                             endpoint.path.lstrip('/'))

    decorator = None
    if endpoint.decorate_request:
        decorator = get_function(endpoint.decorate_request)

    method = endpoint.method.lower()
    if method not in ('get', 'post', 'patch', 'put', 'delete'):
        raise KlueException("BUG: method %s for %s is not supported. Only get and post are." %
                            (endpoint.method, endpoint.path))

    grequests_method = getattr(grequests, method)
    if decorator:
        grequests_method = decorator(grequests_method)
    import pprint

    def client(*args, **kwargs):
        """Call the server endpoint and handle marshaling/unmarshaling of parameters/result.

        client takes either a dict of query parameters, or an object representing the unique
        body parameter.
        """

        # Extract custom parameters from **kwargs
        max_attempts = 3
        read_timeout = timeout
        connect_timeout = timeout

        if 'max_attempts' in kwargs:
            max_attempts = kwargs['max_attempts']
            del kwargs['max_attempts']
        if 'read_timeout' in kwargs:
            read_timeout = kwargs['read_timeout']
            del kwargs['read_timeout']
        if 'connect_timeout' in kwargs:
            connect_timeout = kwargs['connect_timeout']
            del kwargs['connect_timeout']

        # Prepare (g)requests arguments
        headers = {'Content-Type': 'application/json'}
        data = None
        params = None

        custom_url = url

        if hasattr(stack.top, 'call_id'):
            headers['KlueCallID'] = stack.top.call_id
        if hasattr(stack.top, 'call_path'):
            headers['KlueCallPath'] = stack.top.call_path

        if endpoint.param_in_path:
            # Fill url with values from kwargs, and remove those params from kwargs
            custom_url = _format_flask_url(url, kwargs)
            if '<' in custom_url:
                # Some arguments were missing
                return ErrorWrapper(error_callback(ValidationError("Missing some arguments to format url: %s" % custom_url)))

        if endpoint.param_in_query:
            # The query parameters are contained in **kwargs
            params = kwargs
            # TODO: validate params? or let the server do that...
        elif endpoint.param_in_body:
            # The body parameter is the first elem in *args
            if len(args) != 1:
                return ErrorWrapper(error_callback(ValidationError("%s expects exactly 1 parameter" % endpoint.handler_client)))
            data = json.dumps(spec.model_to_json(args[0]))

        # TODO: if request times-out, retry a few times, else return KlueTimeOutError
        # Call the right grequests method (get, post...)
        greq = grequests_method(custom_url,
                                data=data,
                                params=params,
                                headers=headers,
                                timeout=(connect_timeout, read_timeout))

        return ClientCaller(greq, custom_url, endpoint.operation, endpoint.method, error_callback, max_attempts)

    return client


def _format_flask_url(url, params):
    # TODO: make this code more robust: error if some params are left unmatched
    # or if url still contains placeholders after replacing
    remove = []
    for name, value in params.iteritems():
        if "<%s>" % name in url:
            url = url.replace("<%s>" % name, str(value))
            remove.append(name)

    for name in remove:
        del params[name]

    return url


class ErrorWrapper():
    """A fake ClientCaller that carries an error occured during preparing the call"""

    def __init__(self, result):
        self.result = result

    def call(self, **kwargs):
        return self.result


class ClientCaller():

    def __init__(self, greq, url, operation, method, error_callback, max_attempts):
        assert max_attempts >= 1
        self.url = url
        self.operation = operation
        self.greq = greq
        self.method = method.upper()
        self.error_callback = error_callback
        self.max_attempts = max_attempts

    def _method_is_safe_to_retry(self):
        return self.method in ('GET', 'PATCH')

    def _call_retry(self, force_retry):
        """Call grequest and retry up to max_attempts times (or none if self.max_attempts=1)"""
        last_exception = None
        for i in range(self.max_attempts):
            try:
                log.info("Calling %s %s" % (self.method, self.url))
                responses = grequests.map([self.greq])
                assert len(responses) == 1, "Expected 1 caller, got %s" % len(responses)
                response = responses[0]

                if response is None:
                    log.warn("Got response None")
                    if self._method_is_safe_to_retry():
                        log.info("Retrying since call is a %s" % self.method)
                        continue
                    else:
                        raise KlueException("Call %s %s returned empty response" % (self.method, self.url))

                return response

            except Exception as e:

                last_exception = e

                retry = force_retry

                if isinstance(e, ReadTimeout):
                    # Log enough to help debugging...
                    log.warn("Got a ReadTimeout calling %s %s" % (self.method, self.url))
                    log.warn("Exception was: %s" % str(e))
                    resp = e.response
                    if not resp:
                        log.info("Requests error has no response.")
                        # TODO: retry=True? Is it really safe?
                    else:
                        b = resp.content
                        log.info("Requests has a response with content: " + pprint.pformat(b))
                    if self._method_is_safe_to_retry():
                        # It is safe to retry
                        log.info("Retrying since call is a %s" % self.method)
                        retry = True

                elif isinstance(e, ConnectTimeout):
                    log.warn("Got a ConnectTimeout calling %s %s" % (self.method, self.url))
                    log.warn("Exception was: %s" % str(e))
                    # ConnectTimeouts are safe to retry whatever the call...
                    retry = True

                if retry:
                    continue
                else:
                    raise e

        # max_attempts has been reached: propagate the last received Exception
        if not last_exception:
            last_exception = Exception("Reached max-attempts (%s). Giving up calling %s %s" % (self.max_attempts, self.method, self.url)
        raise last_exception

    def call(self, force_retry=False):
        response = self._call_retry(force_retry)

        # If the remote-server returned an error, raise it as a local KlueException
        if str(response.status_code) != '200':
            log.warn("Call to %s %s returns error: %s" % (self.method, self.url, response.text))
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
        log.info("Call to %s %s returned an instance of %s" % (self.method, self.url, type(result)))
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
    # TODO: call callers.greq
    responses = grequests.map(client_callers)
    results = []
    for i in xrange(1, len(responses)):
        client_caller = client_callers[i]
        response = responses[i]
        results.append(client_caller._unmarshal(response))
