import logging
from flask import jsonify


log = logging.getLogger(__name__)


class KlueException(Exception):
    code = 'Unknown exception'
    status = 500

    def http_reply(self):
        """Return a Flask reply object describing this error"""
        r = jsonify({
            'status': self.status,
            'error': self.code.upper(),
            'error_description': str(self)
        })
        r.status_code = self.status
        if str(self.status) != "200":
            log.warn("ERROR: caught error and returning %s" % r)
        return r

class ValidationError(KlueException):
    code = 'INVALID_PARAMETER'
    status = 400

class Auth0Exception(KlueException):
    code = 'AUTH0_ERROR'
    status = 401

class WeirdResultException(KlueException):
    pass

class AuthTokenExpiredError(KlueException):
    code = 'TOKEN_EXPIRED'
    status = 401

class AuthInvalidAudienceError(KlueException):
    code = 'INVALID_AUDIENCE'
    status = 401

class AuthDecodeError(KlueException):
    code = 'TOKEN_INVALID_SIGNATURE'
    status = 401

class AuthInvalidHeaderError(KlueException):
    code = 'INVALID_HEADER'
    status = 401

class AuthMissingHeaderError(KlueException):
    code = 'AUTHORIZATION_HEADER_MISSING'
    status = 401

class InternalServerError(KlueException):
    code = 'SERVER_ERROR'
    status = 500
