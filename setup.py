from setuptools import setup
import sys
import os

version = None

if sys.argv[-2] == '--version' and 'sdist' in sys.argv:
    version = sys.argv[-1]
    sys.argv.pop()
    sys.argv.pop()

if 'sdist' in sys.argv and not version:
    raise Exception("Please set a version with --version x.y.z")

if not version:
    if 'sdist' in sys.argv:
        raise Exception("Please set a version with --version x.y.z")
    else:
        path_pkg_info = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'PKG-INFO')
        if os.path.isfile(path_pkg_info):
            with open(path_pkg_info, 'r')as f:
                for l in f.readlines():
                    if 'Version:' in l:
                        _, version = l.split(' ')
                        version = version.strip()
        else:
            print("WARNING: cannot set version in custom setup.py")

print("version: %s" % version)

# read the contents of the README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pymacaron-core',
    version=version,
    url='https://github.com/pymacaron/pymacaron-core',
    license='BSD',
    author='Erwan Lemonnier',
    author_email='erwan@lemonnier.se',
    description='Swagger + Flask + Bravado-core = auto-spawning of API server, client and data objects for Pymacaron',
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'flask>=1.0.4',
        'bravado-core==5.13.2',
        'PyYAML>=5.1.2',
    ],
    tests_require=[
        'nose',
        'mock',
        'responses',
        'pycodestyle'
    ],
    test_suite='nose.collector',
    packages=['pymacaron_core', 'pymacaron_core.swagger'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
