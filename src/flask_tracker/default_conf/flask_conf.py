# coding: utf-8

import os
import re
import pathlib
import re
import unidecode

def slugify(text):
    text = unidecode.unidecode(text).lower()
    return re.sub(r'[\W_]+', '-', text)

HERE = pathlib.Path(__file__).parent
categories_ = []
with (HERE / "categories.txt").open('rt') as f: categories_ = [l.strip() for l in f.readlines()]

DATA_PATH =  '/opt/flask_tracker/data'

database_file_ = os.path.join(DATA_PATH, 'tracker.v3.sqlite')
wiki_contents_dir_ = os.path.join(DATA_PATH, 'wiki')

# ~ ######################################
# ~ main section
# ~ ######################################
HOST = '0.0.0.0'
PORT = 12012
LOG_LEVEL = 'WARNING'

# ~ ######################################
# ~ actions-at-start-up section
# ~ ######################################
# ~ INSERT_USERS_IN_DB = True
# ~ POPULATE_SAMPLE_DB = 50
# ~ FORCE_RESET_DB = True

# ~ ######################################
# ~ flask-admin section
# ~ ######################################
DEBUG = True
ENV = 'development'
TESTING = True
PROPAGATE_EXCEPTIONS = 'console'
SECRET_KEY = 'your-secret-KEY'
DATABASE_FILE = database_file_
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + database_file_
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = False
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# ~ ######################################
# ~ wiki section
# ~ ######################################
ENABLE_WIKI = True
WIKI_CONTENT_DIR = wiki_contents_dir_

# ~ ######################################
# ~ customization section
# ~ ######################################
MAX_OPEN_TASK_PER_USER = 30

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

CATEGORY_TOOLTIP_STRING = "info about how to use the semantic of the field 'category'."
TASK_CATEGORIES = [ (slugify(l), l.capitalize()) for l in categories_ ]

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



