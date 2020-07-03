import yaml
import logging
from pymacaron_core.swagger.server import spawn_server_api
from pymacaron_core.swagger.client import generate_client_callers
from pymacaron_core.swagger.spec import ApiSpec
from pymacaron_core.models import get_model


log = logging.getLogger(__name__)


class APIClient():
    """Object gathering the API's client side code.
    Offers client-side methods to call every server endpoint declared in the API.
    """
    pass


class APIModels():
    """Object mapping constructors of API models to their names"""
    pass


def default_error_callback(e):
    """The default callback for handling exceptions caught in the client and server stubs:
    just raise the exception."""
    raise e


def generate_model_instantiator(model_name, definitions):
    # We need this to localize the value of model_class
    def instantiate_model(*args, **kwargs):
        return definitions.get(model_name)(*args, **kwargs)
    return instantiate_model


class API():
    """Describes a REST client/server API, with sugar coating:
    - easily instantiating the objects defined in the API
    - auto-generation of client code

    usage: See apipool.py
    """

    def __init__(self, name, yaml_str=None, yaml_path=None, timeout=10, error_callback=None, formats=None, do_persist=True, host=None, port=None, local=False, proto=None, verify_ssl=True):
        """An API Specification"""

        self.name = name

        # Is the endpoint callable directly as a python method from within the server?
        # (true is the flask server also serves that api)
        self.local = local

        # Callback to handle exceptions
        self.error_callback = default_error_callback

        # Flag: true if this api has spawned_api
        self.is_server = False
        self.app = None

        # Object holding the client side code to call the API
        self.client = APIClient()

        # Object holding constructors for the API's objects
        self.model = APIModels()

        self.client_timeout = timeout

        # Support versions of PyYAML with and without Loader
        import pkg_resources
        v = pkg_resources.get_distribution("PyYAML").version
        yamlkwargs = {}
        if v > '3.15':
            yamlkwargs['Loader'] = yaml.FullLoader

        if yaml_path:
            log.info("Loading swagger file at %s" % yaml_path)
            swagger_dict = yaml.load(open(yaml_path), **yamlkwargs)
        elif yaml_str:
            swagger_dict = yaml.load(yaml_str, **yamlkwargs)
        else:
            raise Exception("No swagger file specified")

        self.api_spec = ApiSpec(swagger_dict, formats, host, port, proto, verify_ssl)

        model_names = self.api_spec.load_models(do_persist=do_persist)

        # Add aliases to all models into self.model, so a developer may write:
        # 'ApiPool.<api_name>.model.<model_name>(*args)' to instantiate a model
        for model_name in model_names:
            setattr(self.model, model_name, get_model(model_name))

        if error_callback:
            self.error_callback = error_callback

        # Auto-generate client callers, so a developer may write:
        # 'ApiPool.<api_name>.call.login(param)' to call the login endpoint
        self._generate_client_callers()


    def _generate_client_callers(self, app=None):
        # If app is defined, we are doing local calls
        if app:
            callers_dict = generate_client_callers(self.api_spec, self.client_timeout, self.error_callback, True, app)
        else:
            callers_dict = generate_client_callers(self.api_spec, self.client_timeout, self.error_callback, False, None)

        for method, caller in list(callers_dict.items()):
            setattr(self.client, method, caller)


    def spawn_api(self, app, decorator=None):
        """Auto-generate server endpoints implementing the API into this Flask app"""
        if decorator:
            assert type(decorator).__name__ == 'function'
        self.is_server = True
        self.app = app

        if self.local:
            # Re-generate client callers, this time as local and passing them the app
            self._generate_client_callers(app)

        return spawn_server_api(self.name, app, self.api_spec, self.error_callback, decorator)


    def get_version(self):
        """Return the version of the API (as defined in the swagger file)"""
        return self.api_spec.version


    def model_to_json(self, object):
        """Take a model instance and return it as a json struct"""
        return object.to_json()


    def json_to_model(self, model_name, j, validate=False, keep_datetime=False):
        """Take a json strust and a model name, and return a model instance"""
        if validate:
            self.api_spec.validate(model_name, j)
        o = getattr(self.model, model_name)
        return o.from_json(j, keep_datetime=keep_datetime)
