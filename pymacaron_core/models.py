import logging
import types
from copy import deepcopy
from bravado_core.marshal import marshal_model
from bravado_core.unmarshal import unmarshal_model
import bravado_core.model
from pymacaron_core.exceptions import ValidationError
from pymacaron_core.exceptions import PyMacaronModelException
from pymacaron_core.utils import get_function


log = logging.getLogger(__name__)


class Models():
    """Class holding all generated models"""
    pass


def get_model(model_name):
    if hasattr(Models, model_name):
        return getattr(Models, model_name)
    raise ValidationError("Swagger spec has no definition for model %s" % model_name)


class PyMacaronModel(object):
    """Instances of PyMacaron Model are passed to and returned by the API
    endpoints.

    They encapsulate an instance of a Bravado model that holds the instance's
    attributes, they may inherit from a parent class, they can be serialized to
    and from json, they can be loaded from and to a persistent database.

    """

    # Class variables: Name of this model and pymacaron-core ApiSpec of that model
    __model_name = None
    __swagger_dict = None
    __swagger_spec = None

    #
    # Delegate getter/setter/etc to Bravado model
    #

    def __setattr__(self, k, v):
        if k in getattr(self, '__property_names'):
            log.debug("Setting bravado instance %s" % k)
            setattr(getattr(self, '__bravado_instance'), k, v)
        else:
            log.debug("Setting local instance %s" % k)
            super().__setattr__(k, v)


    def __getattr__(self, k):
        # NOTE: overriding __getattr__ is tricky since we need __property_names early,
        # and getattr() is used by hasattr() to check if an attribute exists
        if k.endswith('__property_names'):
            return getattr(self, '__property_names')
        elif k in getattr(self, '__property_names'):
            i = getattr(self, '__bravado_instance')
            return getattr(i, k)
        elif k not in dir(self):
            raise AttributeError("Model '%s' has no attribute %s" % (getattr(self, '__model_name'), k))
        else:
            return getattr(self, k)

    def __delattr__(self, k):
        if k in getattr(self, '__property_names'):
            delattr(getattr(self, '__bravado_instance'), k)
        else:
            super().__delattr__(k)

    def __eq__(self, other):
        log.debug("COMPARING!!!!\n  %s\n  %s" % (self, other))
        if type(self) is not type(other):
            return False
        return getattr(self, '__bravado_instance') == getattr(other, '__bravado_instance')

    def __repr__(self):
        return 'PyMacaron:%s:%s' % (getattr(self, '__model_name'), str(getattr(self, '__bravado_instance')))

    #
    # JSON marshal/unmarshal
    #

    def to_json(self):
        """Return a json representation of this PyMacaron object"""
        log.debug("Marshalling %s into json" % getattr(self, '__model_name'))
        return marshal_model(
            getattr(self, '__swagger_spec'),
            getattr(self, '__swagger_dict'),
            self.to_bravado(),
        )

    @classmethod
    def from_json(cls, j):
        """Take a json dictionary and return a model instance"""
        log.debug("Unmarshalling json into %s" % getattr(cls, '__model_name'))
        m = unmarshal_model(
            getattr(cls, '__swagger_spec'),
            getattr(cls, '__swagger_dict'),
            j
        )
        return cls.from_bravado(m)

    #
    # Methods to cast a PyMacaron Model to/from a Bravado Model
    #

    def to_bravado(self):
        """Return a pure Bravado Model representing self"""

        # Get internal Bravado instance and clone it
        o = getattr(self, '__bravado_instance')
        o = deepcopy(o)

        # Do the same recursively with every nested PyMacaron Model
        for k in getattr(self, '__property_names'):
            v = getattr(o, k)
            if isinstance(v, PyMacaronModel):
                setattr(o, k, v.to_bravado())
            elif type(v) is list:
                for i in range(len(v)):
                    if isinstance(v[i], PyMacaronModel):
                        v[i] = v[i].to_bravado()
        return o

    @classmethod
    def from_bravado(cls, o):
        """Take a bravado Model instance and return a PyMacaron Model instance"""

        # Clone bravado instance and inject it into a matching PyMacaron model instance
        o = deepcopy(o)
        p = cls()
        setattr(p, '__bravado_instance', o)

        # Now cast from bravado to pymacaron models all the attributes of this model
        for k in getattr(p, '__property_names'):
            v = getattr(o, k)
            if isinstance(v, bravado_core.model.Model):
                cls = get_model(v.__class__.__name__)
                setattr(o, k, cls.from_bravado(v))
            elif type(v) is list:
                for i in range(len(v)):
                    if isinstance(v[i], bravado_core.model.Model):
                        cls = get_model(v[i].__class__.__name__)
                        v[i] = cls.from_bravado(v[i])
        return p


def generate_model_class(name=None, bravado_class=None, swagger_dict=None, swagger_spec=None, parent_name=None, persist=None, properties={}):
    """Dynamically generate a pymacaron.models.<model_name> class able to
    instantiate that model.

    :name: the model name, as in the swagger spec
    :parent_name: complete name (module path + class name) of a class that this model should inherit from.
    :param persist: name of a package or class that implements the 'load_from_db' and 'save_to_db' methods.
    """

    if parent_name:
        assert type(parent_name) is str

    if persist:
        assert type(persist) is str

    # Which parents are we inheriting?
    parents = (PyMacaronModel, )
    if parent_name:
        parent_class = get_function(parent_name)
        parents = parents + (parent_class, )

    # Is this model persistent?
    persistence_class = None
    if persist:
        persistence_class = get_function(persist)
        for n in ('load_from_db', 'save_to_db'):
            if not hasattr(persistence_class, n):
                raise PyMacaronModelException("Class %s has no static method '%s'" % (persist, n))

    # Generate the instance's constructor
    def init(self, *args, **kwargs):
        self.__bravado_instance = bravado_class(*args, **kwargs)

        # Add persistence - Monkey-patch the instance method save_to_db
        if persistence_class:
            self.save_to_db = types.MethodType(persistence_class.save_to_db, self)

    # And generate the model's class
    o = type(
        name,
        parents,
        {
            '__init__': init,
            '__model_name': name,
            '__persistence_class__': persist,
            '__property_names': list(properties.keys()),
            '__swagger_spec': swagger_spec,
            '__swagger_dict': swagger_dict,
        },
    )

    if persist:
        # Monkey-patch the class method 'load_from_db'
        def load_from_db(*args, **kwargs):
            return persistence_class.load_from_db(*args, **kwargs)
        o.load_from_db = load_from_db

    # And remember the mapping between this bravado model and its pymacaron model
    setattr(Models, name, o)

    return o
