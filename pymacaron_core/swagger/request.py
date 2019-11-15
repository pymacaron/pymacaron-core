import logging
from werkzeug import FileStorage
from bravado_core.request import IncomingRequest


log = logging.getLogger(__name__)


class FlaskRequestProxy(IncomingRequest):
    """Take a flask.request object and make it look like a
    bravado_core.request.IncomingRequest"""

    path = None
    query = None
    form = None
    headers = None
    _json = None

    def __init__(self, request, has_data):
        self.request = request
        self.query = request.args
        self.path = request.view_args
        self.headers = request.headers
        self.files = {}
        self._json = {}

        if has_data:
            # has_data == True means there are key-value parameters we can extract from the request body

            # If the request contained no data, no need to analyze it further
            if len(self.request.get_data()) == 0:
                return

            # Let's try to convert whatever content-type we got in the request to something json-like
            ctype = self.request.content_type
            if not ctype:
                # If no content-type specified, assume json
                ctype = 'application/json'

            if ctype.startswith('application/x-www-form-urlencoded'):
                # Store the request's form
                self._json = self.request.form.to_dict()

            elif ctype.startswith('multipart/form-data'):
                # Store the request's form and files
                self._json = self.request.form.to_dict()

                # Go through all the objects passed in form-data and try converting to something json-friendly
                files = self.request.files.to_dict()
                for k in list(files.keys()):
                    v = files[k]
                    if type(v) is FileStorage:
                        # In bravado_core.request.IncomingRequest, 'files' contains a dict of param name to content
                        name = v.name
                        self.files[name] = v.read()
                        # Since bravado drops the filename and mimetype, we explicitely add them to the files dict
                        self.files['%s_filename' % name] = v.filename
                        self.files['%s_mimetype' % name] = v.content_type
                    else:
                        raise Exception("Support for multipart/form-data containing %s is not implemented" % type(v))
            else:
                # Assuming we got a json body
                self._json = self.request.get_json(force=True)

    def json(self):
        # Convert a weltkreuz ImmutableDict to a simple python dict
        return self._json
