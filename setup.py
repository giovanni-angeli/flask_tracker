# coding: utf-8

"""See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

import os
import pathlib
from glob import glob
from setuptools import setup, find_packages

HERE = pathlib.Path(__file__).parent
with (HERE / "README.md").open('rt') as f: 
    README = f.read()


VERSION = '0.10.0rc5'

INSTALL_REQUIRES = [
    'jsonschema',  
    "futures",  
    "requests", 
    'sqlalchemy-utils',
    'flask',
    'flask_restful',
    'flask_admin',
    'flask_sqlalchemy',
    'tablib', 
    'waitress',
    'iso8601',
    'isoweek',
    'flask-login',
    'Flask-WTF',
    'email_validator',
    'markdown',
    'unidecode',
    'flask-migrate']

SETUP_KW_ARGS = {
    'name': 'flask_tracker',
    'version': VERSION,
    'long_description_content_type': 'text/x-rst',
    'long_description': README,
    'description': 'flask_tracker',
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
        'console_scripts': [
            'flask_tracker_run=flask_tracker:main',
            'flask_tracker_init=flask_tracker:initialize_instance',],
    },
    'packages': find_packages('src'),
    'package_dir': {'': 'src'},
    'py_modules': [splitext(basename(pth))[0] for pth in glob('src/*.py')],
    'package_data': {
        'flask_tracker': [
            'default_conf/*',
            'templates/*.html',
            'templates/*/*.html',
            'wiki/templates/*.html',
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
