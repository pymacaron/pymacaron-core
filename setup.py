from setuptools import setup

setup(
    name='klue-client-server',
    version='0.0.10',
    url='https://github.com/erwan-lemonnier/klue-client-server',
    license='BSD',
    author='Erwan Lemonnier',
    author_email='erwan@lemonnier.se',
    description='Swagger + Flask + Grequests + Bravado = Client/Server auto-spawning',
    install_requires=[
        'flask',
        'grequests',
        'bravado-core',
        'pyyaml'
    ],
    tests_require=[
        'nose',
        'mock',
        'responses',
        'pep8'
    ],
    test_suite='nose.collector',
    packages=['klue', 'klue.swagger'],
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
