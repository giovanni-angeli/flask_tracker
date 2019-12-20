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


VERSION = '0.3.0rc5'

CONSOLE_SCRIPTS = [
    'flask_tracker=flask_tracker:main',]

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
    'markdown2',]

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
        'console_scripts': CONSOLE_SCRIPTS,
    },
    'packages': find_packages('src'),
    'package_dir': {'': 'src'},
    'py_modules': [splitext(basename(pth))[0] for pth in glob('src/*.py')],
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
