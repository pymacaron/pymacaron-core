import grequests
import pprint
import jsonschema
import logging
from klue.exceptions import KlueException, ValidationError
from bravado_core.response import unmarshal_response, OutgoingResponse


log = logging.getLogger(__name__)


def generate_client_callers(spec, timeout=10):
    """Return a dict mapping method names to anonymous functions that
    will call the server's endpoint of the corresponding name as
    described in the api defined by the swagger dict and bravado spec"""

    callers_dict = {}

    def mycallback(endpoint):
        if not endpoint.handler_client:
            return

        log.info("Generating client for %s %s" % (endpoint.method, endpoint.path))

        callers_dict[endpoint.handler_client] = _generate_client_caller(spec, endpoint, timeout)

    spec.call_on_each_endpoint(mycallback)

    return callers_dict



def _generate_client_caller(spec, endpoint, timeout):

    url = "%s://%s:%s/%s" % (spec.protocol,
                             spec.host,
                             spec.port,
                             endpoint.path)

    def client(*args, **kwargs):
        """Call the server endpoint and handle marshaling/unmarshaling of parameters/result.

        client takes either a dict of query parameters, or an object representing the unique
        body parameter.
        """

        headers = {}
        data = None
        params = None

#         if endpoint.has_auth:
#             # Re-use the token of the currently authenticated user
#             top = stack.top
#             if not top:
#                 raise KlueException("BUG: no stack.top. Is there an authenticated user in the context?")
#             payload = top.current_user
#             if not payload:
#                 raise KlueException("BUG: stack.top.current_user contains no payload. Is there an authenticated user in the context?")
#             token = payload['token']
#             if not token:
#                 raise KlueException("BUG: no payload in stack.top. Is there an authenticated user in the context?")
#             headers = {"Authorization": "Bearer %s" % token}

        if endpoint.param_in_query:
            # The query parameters are contained in **kwargs
            params = kwargs
            # TODO: validate params? or let the server do that...
        elif endpoint.param_in_body:
            # The body parameter is the first elem in *args
            if len(args) != 1:
                raise ValidationError("%s expects exactly 1 parameter" % endpoint.handler_client)
            data = spec.model_to_json(args[0])

        # TODO: if request times-out, retry a few times, else return KlueTimeOutError
        # Call the right grequests method (get, post...)
        method = endpoint.method.lower()
        if method not in ('get', 'post'):
            raise KlueException("BUG: method %s for %s is not supported. Only get and post are." %
                                (endpoint.method, endpoint.path))

        greq = getattr(grequests, method)(url,
                                          data=data,
                                          params=params,
                                          headers=headers,
                                          timeout=timeout)

        return ClientCaller(greq, endpoint.operation, endpoint.method, endpoint.path)

    return client


class ClientCaller():

    def __init__(self, greq, operation, method, path):
        self.operation = operation
        self.greq = greq
        self.method = method
        self.path = path

    def call(self):
        # TODO: add retry handler to map
        responses = grequests.map([self.greq])
        assert len(responses) == 1
        response = responses[0]

        # If the remote-server returned an error, raise it as a local KlueException
        if str(response.status_code) != '200':
            if 'error_description' in response.text:
                # We got a KlueException. UGLY FRAGILE CODE. To be replaced by proper exception scheme
                j = response.json()
                log.warn("Call to %s %s failed returned code %s: %s" %
                         (self.method, self.path, response.status_code, j))
                k = KlueException(j.get('error_description', ''))
                k.status = response.status_code
                k.error = j.get('error', '')
                raise k
            else:
                # Unknown exception...
                k = KlueException(response.text)
                k.status = response.status_code
                k.error = 'UNKNOWN_REMOTE_ERROR'
                raise k
        else:
            result = self._unmarshal(response)
            return result

    def _unmarshal(self, response):
        # Now transform the request's Response object into an instance of a
        # swagger model
        try:
            result = unmarshal_response(response, self.operation)
        except jsonschema.exceptions.ValidationError as e:
            new_e = ValidationError(str(e))
            return new_e.http_reply()
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
