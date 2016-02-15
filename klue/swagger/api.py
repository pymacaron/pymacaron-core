import pprint
import yaml
import logging
from bravado_core.spec import Spec
from klue.swagger.server import spawn_server_api
from klue.swagger.client import generate_client_callers
from klue.swagger.spec import ApiSpec

log = logging.getLogger(__name__)


class APIClient():
    """Object gathering the API's client side code.
    Offers client-side methods to call every server endpoint declared in the API.
    """
    pass


class APIModels():
    """Object mapping constructors of API models to their names"""
    pass


def generate_model_instantiator(model_class):
    # We need this to localize the value of model_class
    def instantiate_model(*args, **kwargs):
        return model_class(*args, **kwargs)
    return instantiate_model


def default_error_callback(e):
    """The default callback for handling exceptions caught in the client and server stubs:
    just raise the exception."""
    raise e


class API():
    """Describes a REST client/server API, with sugar coating:
    - easily instantiating the objects defined in the API
    - auto-generation of client code

    usage: See apipool.py
    """

    # The API's swagger representation
    api_spec = None

    # Object holding the client side code to call the API
    client = APIClient()

    # Object holding constructors for the API's objects
    model = APIModels()

    # Default timeout when calling server endpoint, in sec
    client_timeout = 10

    # Callback to handle exceptions
    error_callback = default_error_callback

    # Flag: true if this api has spawned_api
    is_server = False

    def __init__(self, yaml_str=None, yaml_path=None, timeout=None, error_callback=None, formats=None):
        """An API Specification"""

        if yaml_path:
            log.info("Loading swagger file at %s" % yaml_path)
            swagger_dict = yaml.load(open(yaml_path))
        elif yaml_str:
            swagger_dict = yaml.load(yaml_str)

        self.api_spec = ApiSpec(swagger_dict, formats)

        if timeout:
            self.client_timeout = timeout

        if error_callback:
            self.error_callback = error_callback

        # Auto-generate class methods for every object model defined
        # in the swagger spec, calling that model's constructor
        # Ex:
        #     klue_api.Version(version='1.2.3')   => return a Version object
        for model_name in self.api_spec.definitions:
            model_class = self.api_spec.definitions[model_name]
            setattr(self.model, model_name, generate_model_instantiator(model_class))

        # Auto-generate client callers
        # so we can write
        # api.call.login(param)  => call /v1/login/ on server with param as json parameter
        callers_dict = generate_client_callers(self.api_spec, self.client_timeout, self.error_callback)
        for method, caller in callers_dict.items():
            setattr(self.client, method, caller)


    def spawn_api(self, app, decorator=None):
        """Auto-generate server endpoints implementing the API into this Flask app"""
        if decorator:
            assert type(decorator).__name__ == 'function'
        self.is_server = True
        return spawn_server_api(app, self.api_spec, self.error_callback, decorator)


    def get_version(self):
        """Return the version of the API (as defined in the swagger file)"""
        return self.api_spec.version
