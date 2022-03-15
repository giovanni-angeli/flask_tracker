# coding: utf-8

import os
import pathlib
import re
import json


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
sample_task_content_file_path = pathlib.Path.joinpath(HERE, "sample_task_content.txt")

if not sample_task_content_file_path.exists():
    with sample_task_content_file_path.open('wt') as f:
        _text = '''
            ###  Contesto

            *describe here the context of this task*

            ###  Prerequisiti

              1. primo  requirement
              1. secondo requirement
              1. terzo  requirement

            ###  Obiettivo

            *describe here what this task is aimed to*

            ####  Passi Previsti

              1. primo  step
              1. secondo step
              1. terzo  step

            ####  Passi Eseguiti




            ____________

        '''
        f.write(_text)

with sample_task_content_file_path.open('rt') as f:
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


ROLE_CAPABILITY_MAP = {
    'admin': {
        'default': '*',
    },
    'administrative_manager': {
        'default': '',
        # ~ 'user': 'r',
        'task': 'r',
        'project': 'r',
        'milestone': 'r',
        'customer': 'r',
        'history': 'r',
        'work_time': '*',
        'order': 'r',
        'attachment': 'r',
        'claim': 'r',
        'improvement': 'r',
    },
    'tech_manager': {
        'default': '',
        'user': 'r',
        'task': 'rce',
        'project': '*',
        'milestone': '*',
        'history': 'rc',
        'customer': '',
        'work_time': '*',
        'order': '*',
        'attachment': '*',
        'claim': 'rce',
        'improvement': 'rce',
    },
    'service': {
        'default': '',
        'attachment': '*',
        'claim': '*',
        'improvement': '*',
        'history': 'r',
    },
    'guest': {'default': 'r'},
    'suspended': {'default': ''}, }

IPV4_BY_HOSTNAME = True

REGISTRY_MODELS = [
    ('Color Tester', 'Color Tester'),
    ('Color Lab', 'Color Lab'),
    ('Desk', 'Desk'),
    ('Thor', 'Thor'),
    ('CR4', 'CR4'),
    ('CR6', 'CR6'),
]

JSONSCHEMA_REGISTRY = {}
with (HERE / "jsonschema_registry.json").open('r') as f:
    data = f.read()
    JSONSCHEMA_REGISTRY = json.loads(data)
    # FW_SW_VERSIONS = data
