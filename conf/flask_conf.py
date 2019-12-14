# coding: utf-8

import os

database_file_ = os.path.join('/opt/flask_tracker/data', 'tracker.v0.sqlite')

HOST = '127.0.0.1'
PORT = 8080
LOG_LEVEL = 'WARNING'

INSERT_ADMIN_USER_IN_DB = True
POPULATE_SAMPLE_DB = True
FORCE_RESET_DB = True

DEBUG = True
ENV = 'development'
TESTING = True
PROPAGATE_EXCEPTIONS = 'console'
SECRET_KEY = os.environ.get('SECRET_KEY') or '1234567890'
DATABASE_FILE = database_file_
# ~ SQLALCHEMY_DATABASE_URI = 'sqlite://' # in memory db
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + database_file_
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = False
MAX_CONTENT_LENGTH = 4 * 1024 * 1024
