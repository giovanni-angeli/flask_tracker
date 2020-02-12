# coding: utf-8

import os
import pathlib
import re


def slugify(text):
    try:
        import unidecode
        text = unidecode.unidecode(text).lower()
    except ModuleNotFoundError:
        text = text.lower()

    return re.sub(r'[\W_]+', '-', text)


HERE = pathlib.Path(__file__).parent
categories_ = []
with (HERE / "categories.txt").open('rt') as f:
    categories_ = [l.strip() for l in f.readlines()]

sample_task_content_lines_ = []
with (HERE / "sample_task_content.txt").open('rt') as f:
    sample_task_content_lines_ = f.readlines()

# ~ DATA_PATH =  '/mnt/dati/flask_tracker/data'
DATA_PATH = '/opt/flask_tracker/data'

database_file_ = os.path.join(DATA_PATH, 'tracker.vX.sqlite')
wiki_contents_dir_ = os.path.join(DATA_PATH, 'wiki')

# ~ ######################################
# ~ main section
# ~ ######################################
HOST = '0.0.0.0'
PORT = 12012
LOG_LEVEL = 'WARNING'

# ~ ######################################
# ~ email client section
# ~ ######################################
# EMAIL_CREDENTIALS_PATH = "/opt/flask_tracker/conf/gmail.FT.credentials"
# IMAP_HOST_PORT = ('imap.gmail.com:993')
# SMTP_HOST_PORT = ('smtp.gmail.com:465')
# CHECK_EMAIL_TIME_STEP = 1*60*60

# ~ ######################################
# ~ actions-at-start-up section
# ~ ######################################
# INSERT_USERS_IN_DB = True
# POPULATE_SAMPLE_DB = 50
# FORCE_RESET_DB = True

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
SUPERVISOR_WEB_PORT = 9001

CAN_DELETE_TASK = False
CAN_DELETE_WORKTIME = True
CAN_EDIT_WORKTIME = True

ATTACHMENT_PATH = os.path.join(DATA_PATH, 'attachments')

MAX_OPEN_TASK_PER_USER = 30

USERS = (
    ('admin', 'admin', 'alfadispenser.com', 'admin', 5),
    ('test', 'test', '', 'guest', 0),
    ('anonymous', '', '', 'guest', 0),)

SAMPLE_TASK_CONTENT = """
###  Context

...

*describe here the context of this task*

###  Prerequisites

  1. first  requirement
  1. second requirement
  1. third  requirement

###  Obiettivo

*describe here what this task is aimed to*

####  Steps to be done

  1. first  step
  1. second  step
  1. third  step

####  Done steps
___________

"""

SAMPLE_CLAIM_CONTENT = """

###  header


####  footer
___________

"""

DEPARTMENTS = [
    ('SW', 'SW'),
    ('FW', 'FW'),
    ('mechanics', 'Mechanics'),
    ('electronics', 'Electronics'),
    ('lab', 'Lab'), ]

CLAIM_GROUPS = [
    ('gruppo_colorante', 'Gruppo Colorante'),
    ('gruppo_base', 'Gruppo Base'),
    ('EV_colorante', 'EV Colorante'),
    ('EV_base', 'EV Base'),
    ('autocap', 'Autocap'),
    ('umidificatore', 'Umidificatore'),
    ('parti_elettroniche', 'Parti Elettroniche'),
    ('altre_parti_meccaniche', 'Altre Parti Meccaniche')]

ITEM_PRIORITIES = [
    ('low', 'Low'),
    ('high', 'High'),
    ('normal', 'Normal')]

CATEGORY_DESCRIPTION = "info about how to use the semantic of the field 'category'."
TASK_CATEGORIES = [(slugify(l), l.capitalize()) for l in categories_]

ITEM_STATUSES = [
    ('new', 'New'),
    ('open', 'Open'),
    ('in_progress', 'In Progress'),
    ('suspended', 'Suspended'),
    ('test', 'Test'),
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
        'order': '*',
        'attachment': '*',
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
        'order': '*',
        'attachment': '*',
    },
    'guest': {'default': 'r'},
    'suspended': {'default': ''}, }
