# coding: utf-8

import os

# ~ ######################################
# ~ main section
# ~ ######################################
HOST = '127.0.0.1'
PORT = 12012
LOG_LEVEL = 'WARNING'

# ~ ######################################
# ~ actions-at-start-up section
# ~ ######################################
INSERT_USERS_IN_DB = True
POPULATE_SAMPLE_DB = 50
# ~ FORCE_RESET_DB = True

# ~ ######################################
# ~ flask-admin section
# ~ ######################################
database_file_ = os.path.join('/opt/flask_tracker/data', 'tracker.v1.sqlite')
DEBUG = True
ENV = 'development'
TESTING = True
PROPAGATE_EXCEPTIONS = 'console'
SECRET_KEY = os.environ.get('SECRET_KEY') or '1*3*5*7*0'
DATABASE_FILE = database_file_
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + database_file_
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = False
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# ~ ######################################
# ~ customization section
# ~ ######################################
MAX_OPEN_TASK_PER_USER = 30
TASK_TAGS = ('fattibilita', 'pianificazione', 'design', 'prototipo', 'preserie') 

USERS = (
    ('admin',    'admin', 'alfadispenser.com'   , 'admin', 5),
    ('test',    'test', ''   , 'guest', 0),
    ('anonymous',    '', ''   , 'guest', 0),)

SAMPLE_TASK_CONTENT = """
####  Overview

*describe here the context of this task*

####  Prerequisites

1. first requirement
1. second requirement
1. third requirement

####  Goal

*describe here what this task is aimed to*

####  Steps

1. first step
1. second step
1. third step
____________

"""

DEPARTMENTS = [
    ('SW', 'SW'),
    ('FW', 'FW'),
    ('mechanical', 'Mechanical'),
    ('electronics', 'Electronics'),
    ('lab', 'Lab'),]

TASK_PRIORITIES = [
    ('low', 'Low'),
    ('high', 'High'),
    ('normal', 'Normal')]

TASK_STATUSES = [
    ('new', 'New'),
    ('open', 'Open'),
    ('in_progress', 'In Progress'),
    ('suspended', 'Suspended'),
    ('closed', 'Closed'),
    ('invalid', 'Invalid')]

ROLES_CAPABILITIES_MAP = {
    'admin': {'default': '*'},
    'administrative_manager': {
        'default': '',
        'user': '*',
        'task': '*',
        'project': '',
        'milestone': '*',
        'order': '*',
        'customer': '*',
        'work_time': '*',
    },
    'tech_manager': {
        'default': '',
        'user': '',
        'task': '*',
        'project': '*',
        'milestone': '*',
        'order': '',
        'customer': '',
        'work_time': '*',
    },
    'guest': {'default': 'r'},
    'suspended': {'default': ''}, }



