from setuptools import setup
import sys
import os

version = None

if sys.argv[-2] == '--version' and sys.argv[-3] == 'sdist':
    version = sys.argv[-1]
    sys.argv.pop()
    sys.argv.pop()

if sys.argv[1] == 'sdist' and not version:
    raise Exception("Please set a version with --version x.y.z")

if not version:
    if sys.argv[1] == 'sdist':
        raise Exception("Please set a version with --version x.y.z")
    else:
        path_pkg_info = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'PKG-INFO')
        if os.path.isfile(path_pkg_info):
            with open(path_pkg_info, 'r')as f:
                for l in f.readlines():
                    if 'Version' in l:
                        _, version = l.split(' ')
        else:
            print("WARNING: cannot set version in custom setup.py")

print("version: %s" % version)

setup(name='klue-client-server',
      version=version,
      description='Library of code common to all pnt backends',
      url='https://bitbucket.org/peopleandthings/backend-common',
      author='Erwan Lemonnier',
      author_email='erwan@lemonnier.se',
      packages=['pnt_common', 'pnt_common.swagger'],
      zip_safe=False)
