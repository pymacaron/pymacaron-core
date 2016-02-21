import pprint
import yaml
from klue.swagger.api import API
from bravado_core.spec import Spec

apis = {}

class ApiPool():
    """Store a pool of API objects, each describing one Swagger API.

    USAGE:

    To load an API:
      api = ApiPool.add('klue', 'klue-api.yaml')

    This will generate model classes for all definitions in the YAML spec.

    To get this api from the pool, as an API object (see swagger.api):
      api = ApiPool.klue

    To instantiate one of the model object:
      api.model.Credentials(user='foo', password='bar')

    To spawn all routes associated with the server side of that API:
      api.spawn_api(flask_app)

    To call a remote server endpoint from within the client:
      param = api.model.Param(..)
      result = api.client.server_method(param)

    Where result is an instance of the model returned by the endpoint
    bound to 'server_method' according to the 'x-bind-client' key in
    the YAML file.
    """

    @classmethod
    def add(self, name, **kwargs):
        api = API(name, **kwargs)
        global apis
        apis[name] = api
        setattr(ApiPool, name, api)
        return api

    @property
    def current_server_name(self):
        for name, api in apis.iteritems():
            if api.is_server:
                return name
        return ''

    @property
    def current_server_api(self):
        for name, api in apis.iteritems():
            if api.is_server:
                return api
        return None
