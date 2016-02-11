import logging
from flask import jsonify


log = logging.getLogger(__name__)


class KlueException(Exception):
    code = 'UNKNOWN_EXCEPTION'
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


# Match an error code to a exception class name and a status code
code_classname_status = [
    ('INVALID_PARAMETER', 'ValidationError', 400),
    ('AUTH0_ERROR', 'Auth0Exception', 401),
    ('UNKNOWN_EXCEPTION', 'WeirdResultException', 500),
    ('TOKEN_EXPIRED', 'AuthTokenExpiredError', 401),
    ('INVALID_AUDIENCE', 'AuthInvalidAudienceError', 401),
    ('TOKEN_INVALID_SIGNATURE', 'AuthDecodeError', 401),
    ('INVALID_HEADER', 'AuthInvalidHeaderError', 401),
    ('AUTHORIZATION_HEADER_MISSING', 'AuthMissingHeaderError', 401),
    ('SERVER_ERROR', 'InternalServerError', 500),
]

# Generate all exception classes
code_to_class = {}
for code, classname, status in code_classname_status:
    log.debug("Generating exception class %s(%s, %s)" % (classname, code, status))
    myexception = type(classname, (KlueException,), {"code": code, "status": status})
    globals()[classname] = myexception

    assert code not in code_to_class
    code_to_class[code] = myexception



def responsify(error):
    """Take an Error model and return it as a Flask response"""
    assert str(type(error).__name__) == 'Error'
    if error.error in code_to_class:
        e = code_to_class[error.error](error.error_description)
        return e.http_reply()
    else:
        return KlueException("Caught un-mapped error: %s" % error).http_reply()
