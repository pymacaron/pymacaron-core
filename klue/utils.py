import traceback
from importlib import import_module
from klue.exceptions import KlueException

def get_function(pkgpath):
    """Take a full path to a python method or class, for example
    mypkg.subpkg.method and return the method or class (after importing the
    required packages)
    """
    # Extract the module and function name from pkgpath
    elems = pkgpath.split('.')
    if len(elems) <= 1:
        raise KlueException("Path %s is too short. Should be at least module.func." % elems)
    func_name = elems[-1]
    func_module = '.'.join(elems[0:-1])

    # Load the function's module and get the function
    try:
        m = import_module(func_module)
        f = getattr(m, func_name)
        return f
    except Exception as e:
        t = traceback.format_exc()
        raise KlueException("Failed to import %s: %s\nTrace:\n%s" % (pkgpath, str(e), t))
