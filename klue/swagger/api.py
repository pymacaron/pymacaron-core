import pprint
import types
import yaml
import logging
from bravado_core.spec import Spec
from klue.swagger.server import spawn_server_api
from klue.swagger.client import generate_client_callers
from klue.swagger.spec import ApiSpec
from klue.exceptions import KlueException
from klue.utils import get_function

log = logging.getLogger(__name__)


class APIClient():
    """Object gathering the API's client side code.
    Offers client-side methods to call every server endpoint declared in the API.
    """
    pass


class APIModels():
    """Object mapping constructors of API models to their names"""
    pass


def generate_model_instantiator(model_name, definitions):
    # We need this to localize the value of model_class
    def instantiate_model(*args, **kwargs):
        return definitions.get(model_name)(*args, **kwargs)
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

    # The api's name
    name = None

    def __init__(self, name, yaml_str=None, yaml_path=None, timeout=None, error_callback=None, formats=None, do_persist=True, host=None, port=None):
        """An API Specification"""

        self.name = name

        if yaml_path:
            log.info("Loading swagger file at %s" % yaml_path)
            swagger_dict = yaml.load(open(yaml_path))
        elif yaml_str:
            swagger_dict = yaml.load(yaml_str)
        else:
            raise Exception("No swagger file specified")

        self.api_spec = ApiSpec(swagger_dict, formats, host, port)

        if timeout:
            self.client_timeout = timeout

        if error_callback:
            self.error_callback = error_callback

        # Auto-generate class methods for every object model defined
        # in the swagger spec, calling that model's constructor
        # Ex:
        #     klue_api.Version(version='1.2.3')   => return a Version object
        for model_name in self.api_spec.definitions:
            model_generator = generate_model_instantiator(model_name, self.api_spec.definitions)

            # Associate model generator to ApiPool().<api_name>.model.<model_name>
            setattr(self.model, model_name, model_generator)

            # Make this bravado-core model persistent?
            if do_persist:
                spec = swagger_dict['definitions'][model_name]
                if 'x-persist' in spec:
                    self._make_persistent(model_name, spec['x-persist'])

        # Auto-generate client callers
        # so we can write
        # api.call.login(param)  => call /v1/login/ on server with param as json parameter
        callers_dict = generate_client_callers(self.api_spec, self.client_timeout, self.error_callback)
        for method, caller in callers_dict.items():
            setattr(self.client, method, caller)


    #
    # WARNING: ugly piece of monkey-patching below. Hopefully will replace
    # with native bravado-core code in the future...
    #
    def _make_persistent(self, model_name, pkg_name):
        """Monkey-patch object persistence (ex: to/from database) into a
        bravado-core model class"""

        # Load class at path pkg_name
        c = get_function(pkg_name)
        for name in ('load_from_db', 'save_to_db'):
            if not hasattr(c, name):
                raise KlueException("Class %s has no static method '%s'" % (pkg_name, name))

        log.info("Making %s persistent via %s" % (model_name, pkg_name))

        # Replace model generator with one that adds 'save_to_db' to every instance
        model = getattr(self.model, model_name)
        n = self._wrap_bravado_model_generator(model, c.save_to_db)
        setattr(self.model, model_name, n)

        # Add class method load_from_db to model generator
        model = getattr(self.model, model_name)
        setattr(model, 'load_from_db', c.load_from_db)

    def _wrap_bravado_model_generator(self, model, method):

        def new_creator(*args, **kwargs):
            r = model(*args, **kwargs)
            r.save_to_db = types.MethodType(method, r)
            return r

        return new_creator

    #
    # End of ugly-monkey-patching
    #

    def spawn_api(self, app, decorator=None):
        """Auto-generate server endpoints implementing the API into this Flask app"""
        if decorator:
            assert type(decorator).__name__ == 'function'
        self.is_server = True
        return spawn_server_api(self.name, app, self.api_spec, self.error_callback, decorator)


    def get_version(self):
        """Return the version of the API (as defined in the swagger file)"""
        return self.api_spec.version


    def model_to_json(self, object):
        """Take a model instance and return it as a json struct"""
        return self.api_spec.model_to_json(object)


    def json_to_model(self, model_name, j):
        """Take a json strust and a model name, and return a model instance"""
        return self.api_spec.json_to_model(model_name, j)
