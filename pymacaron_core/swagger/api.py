import types
import yaml
import logging
from pymacaron_core.swagger.server import spawn_server_api
from pymacaron_core.swagger.client import generate_client_callers
from pymacaron_core.swagger.spec import ApiSpec
from pymacaron_core.exceptions import PyMacaronCoreException
from pymacaron_core.utils import get_function

log = logging.getLogger(__name__)


# Monkey patch bravado-core's __str__ and __repr__ - REQUIRES v 5.10.0
log.debug("Monkey-patching Bravado 5.10.0's Model.__str__()")
from bravado_core.model import Model
Model.__str__ = lambda x: "<swagger %s>" % x.__class__.__name__


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

        if yaml_path:
            log.info("Loading swagger file at %s" % yaml_path)
            swagger_dict = yaml.load(open(yaml_path))
        elif yaml_str:
            swagger_dict = yaml.load(yaml_str)
        else:
            raise Exception("No swagger file specified")

        self.api_spec = ApiSpec(swagger_dict, formats, host, port, proto, verify_ssl)

        if error_callback:
            self.error_callback = error_callback

        # Auto-generate class methods for every object model defined
        # in the swagger spec, calling that model's constructor
        # Ex:
        #     my_api.Version(version='1.2.3')   => return a Version object
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
        self._generate_client_callers()

    def _generate_client_callers(self, app=None):
        # If app is defined, we are doing local calls
        if app:
            callers_dict = generate_client_callers(self.api_spec, self.client_timeout, self.error_callback, True, app)
        else:
            callers_dict = generate_client_callers(self.api_spec, self.client_timeout, self.error_callback, False, None)

        for method, caller in list(callers_dict.items()):
            setattr(self.client, method, caller)


    def _make_persistent(self, model_name, pkg_name):
        """Monkey-patch object persistence (ex: to/from database) into a
        bravado-core model class"""

        #
        # WARNING: ugly piece of monkey-patching below. Hopefully will replace
        # with native bravado-core code in the future...
        #

        # Load class at path pkg_name
        c = get_function(pkg_name)
        for name in ('load_from_db', 'save_to_db'):
            if not hasattr(c, name):
                raise PyMacaronCoreException("Class %s has no static method '%s'" % (pkg_name, name))

        log.info("Making %s persistent via %s" % (model_name, pkg_name))

        # Replace model generator with one that adds 'save_to_db' to every instance
        model = getattr(self.model, model_name)
        n = self._wrap_bravado_model_generator(model, c.save_to_db, pkg_name)
        setattr(self.model, model_name, n)

        # Add class method load_from_db to model generator
        model = getattr(self.model, model_name)
        setattr(model, 'load_from_db', c.load_from_db)

    def _wrap_bravado_model_generator(self, model, method, pkg_name):

        def new_creator(*args, **kwargs):
            r = model(*args, **kwargs)
            setattr(r, 'save_to_db', types.MethodType(method, r))
            setattr(r, '__persistence_class__', pkg_name)
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
        return self.api_spec.model_to_json(object)


    def json_to_model(self, model_name, j, validate=False):
        """Take a json strust and a model name, and return a model instance"""
        if validate:
            self.api_spec.validate(model_name, j)
        return self.api_spec.json_to_model(model_name, j)
