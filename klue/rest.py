import re
import jwt
import logging
import base64
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from flask.ext.cors import cross_origin
from flask import request, jsonify
from pnt_common.config import get_config
from pnt_common.auth import authenticate_http_request
from pnt_common.exceptions import PntException

from functools import wraps


log = logging.getLogger(__name__)


try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack

"""Library of common functions related to the REST api"""

def get_userid():
    """Return the authenticated user's id, i.e. its auth0 id"""
    current_user = stack.top.current_user
    get_logger().debug("Current user is: %s" % current_user)
    return current_user['sub']


def http_reply(data, code=200):
    """Send an http reply back to the caller of the REST api.

    Response consists of the jsonified error and given HTTP error code.
    """
    if not re.match(r'^\d\d\d$', "%s" % code):
        raise Exception("BUG: code %s is not a valid http code (data: %s)" % (code, data))
    r = jsonify(data)
    r.status_code = code
    get_logger().debug("Replying %s" % code)
    return r


def requires_auth(f):
    """A decorator for flask api methods that validates auth0 tokens, hence ensuring
    that the user is authenticated. Code coped from:
    https://github.com/auth0/auth0-python/tree/master/examples/flask-api
    """

    @wraps(f)
    def decorated(*args, **kwargs):

        try:
            authenticate_http_request()
        except PntException as e:
            return e.http_reply()

        return f(*args, **kwargs)

    return decorated

#
# Below are Flask setup steps common to all backend servers
#

@cross_origin(headers=['Content-Type', 'Authorization'])
@requires_auth
def secured_ping():
    get_logger().debug("Replying secured_ping:ok")
    return "{ 'ping': 'ok' }"


@cross_origin(headers=['Content-Type', 'Authorization'])
def ping():
    get_logger().debug("Replying ping:ok")
    return "{ 'ping': 'ok' }"


def start_server(app, port, debug, no_ping=False):
    """Start the flask app, adding the /ping and /secured/ping routes common to
    all backend servers"""

    if not no_ping:
        app.add_url_rule('/ping', 'ping', ping)
        app.add_url_rule('/secured/ping', 'secured_ping', secured_ping)

    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.
    if debug:
        app.debug = debug
        app.run(host='0.0.0.0', port=port)
    else:
        http_server = HTTPServer(WSGIContainer(app))
        http_server.listen(port)
        IOLoop.instance().start()
