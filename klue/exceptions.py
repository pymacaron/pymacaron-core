import logging
from flask import jsonify


log = logging.getLogger(__name__)


class KlueException(Exception):
    status_code = 500

class ValidationError(KlueException):
    status_code = 400

class InternalServerError(KlueException):
    status_code = 500

class MergeApisException(KlueException):
    status_code = 500


def add_error_handlers(app):
    """Add custom error handlers for KlueExceptions to the app"""

    def handle_validation_error(error):
        response = jsonify({'message': str(error)})
        response.status_code = error.status_code
        return response

    app.errorhandler(ValidationError)(handle_validation_error)
