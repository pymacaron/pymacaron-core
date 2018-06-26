import requests
import pprint
import jsonschema
import json
import logging
import time
import urllib.request
import urllib.parse
import urllib.error
from requests.exceptions import ReadTimeout, ConnectTimeout
from pymacaron_core.exceptions import PyMacaronCoreException, ValidationError
from pymacaron_core.utils import get_function
from bravado_core.response import unmarshal_response


log = logging.getLogger(__name__)


try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack


def generate_client_callers(spec, timeout, error_callback, local, app):
    """Return a dict mapping method names to anonymous functions that
    will call the server's endpoint of the corresponding name as
    described in the api defined by the swagger dict and bravado spec"""

    callers_dict = {}

    def mycallback(endpoint):
        if not endpoint.handler_client:
            return

        log.info("Generating client for %s %s" % (endpoint.method, endpoint.path))

        callers_dict[endpoint.handler_client] = _generate_client_caller(spec, endpoint, timeout, error_callback, local, app)

    spec.call_on_each_endpoint(mycallback)

    return callers_dict


def _generate_request_arguments(url, spec, endpoint, headers, args, kwargs):
    # Prepare (g)requests arguments
    data = None
    params = None
    custom_url = url

    if hasattr(stack.top, 'call_id'):
        headers['PymCallID'] = stack.top.call_id
    if hasattr(stack.top, 'call_path'):
        headers['PymCallPath'] = stack.top.call_path

    if endpoint.param_in_path:
        # Fill url with values from kwargs, and remove those params from kwargs
        custom_url = _format_flask_url(url, kwargs)

    if endpoint.param_in_query:
        # The query parameters are contained in **kwargs
        params = kwargs
        # TODO: validate params? or let the server do that...
    elif endpoint.param_in_body:
        # The body parameter is the first elem in *args
        if len(args) != 1:
            raise ValidationError("%s expects exactly 1 parameter" % endpoint.handler_client)
        data = json.dumps(spec.model_to_json(args[0]))

    # Prune undefined parameters that would otherwise be turned into '=None'
    # query params
    if params:
        for k in list(params.keys()):
            if params[k] is None:
                del params[k]

    return custom_url, params, data, headers


def _generate_client_caller(spec, endpoint, timeout, error_callback, local, app):

    if local:
        assert app

    # Is the endpoint available locally?
    if local:
        url = endpoint.path.lstrip('/')
    else:
        url = "%s://%s:%s/%s" % (
            spec.protocol,
            spec.host,
            spec.port,
            endpoint.path.lstrip('/')
        )

    # Get eventual decorator and http method
    decorator = None
    if endpoint.decorate_request:
        decorator = get_function(endpoint.decorate_request)

    method = endpoint.method.lower()
    if method not in ('get', 'post', 'patch', 'put', 'delete'):
        raise PyMacaronCoreException("BUG: method %s for %s is not supported. Only get and post are." %
                                     (endpoint.method, endpoint.path))

    # Are we doing a local call?
    if local:
        def local_client(*args, **kwargs):
            """Just call the local method"""
            log.info("Calling %s locally via flask test_client" % (endpoint.path))

            headers = {'Content-Type': 'application/json'}
            headers.update(kwargs.get('request_headers', {}))

            # Remove magic client parameters before passing on
            for k in ('max_attempts', 'read_timeout', 'connect_timeout', 'request_headers'):
                if k in kwargs:
                    del kwargs[k]

            custom_url, params, data, headers = _generate_request_arguments(url, spec, endpoint, headers, args, kwargs)
            if '<' in custom_url:
                # Some arguments were missing
                return error_callback(ValidationError("Missing some arguments to format url: %s" % custom_url))

            if params:
                for k, v in params.items():
                    if isinstance(v, str):
                        params[k] = v.encode('utf-8')
                custom_url = custom_url + '?' + urllib.parse.urlencode(params)
            log.info("Calling with params [%s]" % params)

            with app.test_client() as c:
                requests_method = getattr(c, method)
                if decorator:
                    requests_method = decorator(requests_method)

                response = requests_method(
                    custom_url,
                    data=data,
                    headers=headers
                )

            return response_to_result(response, method, custom_url, endpoint.operation, error_callback)

        return local_client

    # Else call over HTTP/HTTPS
    requests_method = getattr(requests, method)
    if decorator:
        requests_method = decorator(requests_method)

    def client(*args, **kwargs):
        """Call the server endpoint and handle marshaling/unmarshaling of parameters/result.

        client takes either a dict of query parameters, or an object representing the unique
        body parameter.
        """

        # Extract custom parameters from **kwargs
        headers = {'Content-Type': 'application/json'}
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
        if 'request_headers' in kwargs:
            headers.update(kwargs['request_headers'])
            del kwargs['request_headers']

        custom_url, params, data, headers = _generate_request_arguments(url, spec, endpoint, headers, args, kwargs)

        if '<' in custom_url:
            # Some arguments were missing
            return error_callback(ValidationError("Missing some arguments to format url: %s" % custom_url))

        # TODO: refactor this left-over from the time of async/grequests support and simplify!
        return ClientCaller(requests_method, custom_url, data, params, headers, read_timeout, connect_timeout, endpoint.operation, endpoint.method, error_callback, max_attempts, spec.verify_ssl).call()

    return client


def _format_flask_url(url, params):
    # TODO: make this code more robust: error if some params are left unmatched
    # or if url still contains placeholders after replacing
    remove = []
    for name, value in params.items():
        if "<%s>" % name in url:
            url = url.replace("<%s>" % name, str(value))
            remove.append(name)

    for name in remove:
        del params[name]

    return url


def response_to_result(response, method, url, operation, error_callback):

    # Monkey patching flask test_client response if necessary
    if not hasattr(response, 'text'):
        data = response.data.decode("utf-8")
        setattr(response, 'text', data)
        j = json.loads(data)

        def get_json():
            return j

        setattr(response, 'json', get_json)

    # If the remote-server returned an error, raise it as a local PyMacaronCoreException
    if str(response.status_code) != '200':
        log.warn("Call to %s %s returns error: %s" % (method, url, response.text))
        if 'error_description' in response.text:
            # We got a PyMacaronCoreException: unmarshal it and return as valid
            # return value UGLY FRAGILE CODE. To be replaced by proper
            # exception scheme
            pass
        else:
            # Unknown exception...
            log.info("Unknown exception: " + response.text)
            k = PyMacaronCoreException("Call to %s %s returned unknown exception: %s" % (method, url, response.text))
            k.status_code = response.status_code
            c = error_callback
            if hasattr(c, '__func__'):
                c = c.__func__
            return c(k)

    # Now transform the request's Response object into an instance of a
    # swagger model
    try:
        result = unmarshal_response(response, operation)
    except jsonschema.exceptions.ValidationError as e:
        log.warn("Failed to unmarshal response: %s" % e)
        k = ValidationError("Failed to unmarshal response because: %s" % str(e))
        c = error_callback
        if hasattr(c, '__func__'):
            c = c.__func__
        return c(k)

    log.info("Call to %s %s returned an instance of %s" % (method, url, type(result)))
    return result


class ClientCaller():

    def __init__(self, requests_method, url, data, params, headers, read_timeout, connect_timeout, operation, method, error_callback, max_attempts, verify_ssl):
        assert max_attempts >= 1
        self.requests_method = requests_method
        self.url = url
        self.operation = operation
        self.data = data
        self.params = params
        self.headers = headers
        self.read_timeout = read_timeout
        self.connect_timeout = connect_timeout
        self.method = method.upper()
        self.error_callback = error_callback
        self.max_attempts = max_attempts
        self.verify_ssl = verify_ssl

    def _method_is_safe_to_retry(self):
        return self.method in ('GET', 'PATCH')

    def _call_retry(self, force_retry):
        """Call request and retry up to max_attempts times (or none if self.max_attempts=1)"""
        last_exception = None
        for i in range(self.max_attempts):
            try:
                log.info("Calling %s %s" % (self.method, self.url))
                response = self.requests_method(
                    self.url,
                    data=self.data,
                    params=self.params,
                    headers=self.headers,
                    timeout=(self.connect_timeout, self.read_timeout),
                    verify=self.verify_ssl,
                )

                if response is None:
                    log.warn("Got response None")
                    if self._method_is_safe_to_retry():
                        delay = 0.5 + i * 0.5
                        log.info("Waiting %s sec and Retrying since call is a %s" % (delay, self.method))
                        time.sleep(delay)
                        continue
                    else:
                        raise PyMacaronCoreException("Call %s %s returned empty response" % (self.method, self.url))

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
            last_exception = Exception("Reached max-attempts (%s). Giving up calling %s %s" % (self.max_attempts, self.method, self.url))
        raise last_exception

    def call(self, force_retry=False):
        response = self._call_retry(force_retry)
        return response_to_result(response, self.method, self.url, self.operation, self.error_callback)
