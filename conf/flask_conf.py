# coding: utf-8

import os

database_file_ = os.path.join(os.environ['FT_RUNDATA_ROOT'], 'tracker.v0.sqlite')

HOST = '0.0.0.0'
PORT = 12012
LOG_LEVEL = 'WARNING'
POPULATE_SAMPLE_DB = True

DEBUG = True
ENV = 'development'
TESTING = True
PROPAGATE_EXCEPTIONS = 'console'
# ~ FLASK_ADMIN_SWATCH = 'paper'
SECRET_KEY = os.environ.get('SECRET_KEY') or '1*3*5*7*0'
DATABASE_FILE = database_file_
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + database_file_
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = False
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
