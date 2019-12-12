# coding: utf-8

"""See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

import os
from setuptools import setup, find_packages
from codecs import open
from os import path
from glob import glob


here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(here, '__version__'), encoding='utf-8') as f:
    __version__ = f.read().strip()

CONSOLE_SCRIPTS = [
    'flask_tracker=flask_tracker:main',
]

INSTALL_REQUIRES = [

    'jsonschema',  # ==2.6.0
    "futures",  # ==3.1.1
    "requests",  # ==0.2.0
    'sqlalchemy-utils',
    'flask',
    'flask_restful',
    'flask_admin',
    'flask_sqlalchemy',
    'tablib',  # WSGI server (https://docs.pylonsproject.org/projects/waitress)
    'waitress',  # WSGI server (https://docs.pylonsproject.org/projects/waitress)
    'iso8601',
    'flask-login',
    'markdown2',
]

SETUP_KW_ARGS = {
    'name': 'flask_tracker',
    'version': __version__,
    'description': 'flask_tracker',
    'long_description': long_description,
    'url': 'https://github.com/giovanni-angeli/flask_tracker',
    'author': 'giovanni angeli',
    'author_email': 'giovanni.angeli6@gmail.com',
    'classifiers': [
        'Development Status :: 2 - Pre-Alpha',
        'Programming Language :: Python :: 3',
        'Framework :: Flask', 
    ],
    'install_requires': INSTALL_REQUIRES,
    'entry_points': {
        'console_scripts': CONSOLE_SCRIPTS,
    },
    'packages': find_packages('src'),
    'package_dir': {'': 'src'},
    'py_modules': [splitext(basename(path))[0] for path in glob('src/*.py')],
    'package_data': {
        'flask_tracker': [
            'templates/*.html',
            'templates/*/*.html',
            'static/*.*',
            'static/*/*.*',
            'static/*/*/*.*',
            'static/*/*/*/*.*',
            'static/*/*/*/*/*.*',
        ],
    },
}

if __name__ == "__main__":
    setup(**SETUP_KW_ARGS)
