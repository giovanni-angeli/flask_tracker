# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=broad-except

import os
import uuid
import logging
import traceback
from datetime import datetime

from werkzeug.security import generate_password_hash

from sqlalchemy import event         # pylint: disable=import-error

import flask_sqlalchemy              # pylint: disable=import-error

sqlalchemy_db_ = flask_sqlalchemy.SQLAlchemy()
sqlalchemy_session_ = None
sqlalchemy_Model = sqlalchemy_db_.Model

MODELS_GLOBAL_CONTEXT = {
    'db': sqlalchemy_db_,
    'session': sqlalchemy_db_.session,
    'to_be_deleted_object_list': set([]),
    'table_name2model_classes_map': {}, }


def scan_for_models() -> dict:

    t2m_map = MODELS_GLOBAL_CONTEXT['table_name2model_classes_map']

    if t2m_map:
        pass
    else:
        for n in globals():
            m = globals().get(n)
            try:
                if isinstance(m, flask_sqlalchemy.model.DefaultMeta):
                    flag = issubclass(m, sqlalchemy_Model)
                    flag = flag and issubclass(m, BaseModel)
                    if flag:
                        k = m.__tablename__
                        t2m_map[k] = m
            except Exception as e:
                logging.error(e)

    # ~ logging.warning(
        # ~ " MODELS_GLOBAL_CONTEXT['table_name2model_classes_map']:{}".format(
            # ~ MODELS_GLOBAL_CONTEXT['table_name2model_classes_map']))

    return t2m_map


def generate_id():
    return str(uuid.uuid4())


def insert_admin_user_in_db(app, db):

    args = {'name': 'admin', 
        'password': generate_password_hash('admin'), 
        'role': 'admin', 
        'email': 'admin@gmail.com'}

    with app.app_context():

        try:
            obj = User(**args)
            db.session.add(obj)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logging.error(exc)

def populate_sample_db(app, db, N=20):

    SAMPLE_CONTENT = """

#   Title 1

##  Title 2

### Title 3

####  Title 4
____________

o_list:

1. first
1. secodn
1. third

____________

u_list:

* first
* secodn
* third

and some quoting:

> ## This is a header.
>
> 1.   This is the first list item.
> 2.   This is the second list item.
>
> Here's some example code:
>
>     return shell_exec("echo $input | $markdown_script");

"""

    fixtes = [
        (Customer, {'name': 'Alfa'}),
        (Customer, {'name': 'Comex'}),
        (Project, {'name': 'Thor'}),
        (Project, {'name': 'Desk'}),
        (Project, {'name': 'ColorLab'}),
        (Milestone, {'name': '2020.q4'}),
        (Milestone, {'name': '2020.q2'}),
        (Milestone, {'name': '2020.q2'}),
        (Milestone, {'name': '2020.q3'}),
        (Order, {'name': 'O_0010'}),
        (Order, {'name': 'O_002'}),
        (User, {'name': 'test', 'password': generate_password_hash('test'), 'role': 'guest', 'email': 'test@gmail.com'}),
        (User, {'name': 'anonymous', 'password': generate_password_hash('no'), 'role': 'guest', 'email': ''}),
    ]

    import random
    sts_ = ['new', 'open', 'in_progress', 'suspended', 'closed', 'invalid', 'dead']

    for i in range(N):
        t = (Task, {'name': 'T_%03d' % i, 'content': SAMPLE_CONTENT, 'status': random.choice(sts_)})
        fixtes.append(t)

    for i in range(N):
        u = (User, {'name': 'U_%03d' % i, 'password': generate_password_hash(
            'U_%03d@alfa' % i), 'role': 'guest', 'email': 'U_%03d@alfa.com' % i})
        fixtes.append(u)

    MODELS_GLOBAL_CONTEXT['check_limit_before_insert_disabled'] = True

    with app.app_context():

        for klass, args in fixtes:
            try:
                obj = klass(**args)
                db.session.add(obj)
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                logging.info(exc)
                logging.debug(traceback.format_exc())

    MODELS_GLOBAL_CONTEXT['check_limit_before_insert_disabled'] = False


def reset_db(app, db):

    logging.warning("resetting db")

    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.commit()

followings = sqlalchemy_db_.Table('followings',
                                  sqlalchemy_db_.Column(
                                      'user_id',
                                      sqlalchemy_db_.Unicode,
                                      sqlalchemy_db_.ForeignKey('user.id'),
                                      primary_key=True),
                                  sqlalchemy_db_.Column('task_id', sqlalchemy_db_.Unicode, sqlalchemy_db_.ForeignKey('task.id'), primary_key=True))


class BaseModel(object):                         # pylint: disable=too-few-public-methods

    row_count_limt = 100 * 1000

    db = MODELS_GLOBAL_CONTEXT['db']

    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_modified = db.Column(db.DateTime, default=datetime.utcnow)

    id = db.Column(db.Unicode, primary_key=True, nullable=False, default=generate_id)
    description = db.Column(db.Unicode(200))

    query = None

    @classmethod
    def check_size_limit(cls):
        exceeding_objects = []
        if cls.row_count_limt > 0 and cls.query:
            row_count = cls.query.count()
            exceeding = max(0, row_count - cls.row_count_limt)
            if exceeding > 0:
                exceeding += int(cls.row_count_limt * 0.1)  # below watermark
                exceeding_objects = cls.query.order_by(cls.date_modified).limit(exceeding)
                msg = "cls:{}, row_count:{}, exceeding:{}, exceeding_objects.count():{}".format(
                    cls, row_count, exceeding, exceeding_objects.count())
                logging.warning(msg)
        return exceeding_objects

    def get_id_short(self):
        return self.id[:8]

    id_short = property(get_id_short)


class NamedModel(BaseModel):

    db = MODELS_GLOBAL_CONTEXT['db']

    name = db.Column(db.Unicode(64), nullable=False, unique=True, index=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<{}>{}: {}".format(type(self).__name__[:1], self.id_short, self.__str__())


class Project(NamedModel, sqlalchemy_Model):  # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    tasks = db.relationship('Task', backref='project')

class Customer(NamedModel, sqlalchemy_Model):   # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    orders = db.relationship('Order', backref='customer')

class Order(NamedModel, sqlalchemy_Model):    # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    tasks = db.relationship('Task', backref='order')
    customer_id = db.Column(db.Unicode, db.ForeignKey('customer.id'))
    def __str__(self):
        customer_name = (self.customer.name if self.customer else 'none')
        return "{}.{}".format(customer_name, self.name)

class Milestone(NamedModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    due_date = db.Column(db.DateTime)
    tasks = db.relationship('Task', backref='milestone')

class WorkTime(BaseModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    task_id = db.Column(db.Unicode, db.ForeignKey('task.id'))
    user_id = db.Column(db.Unicode, db.ForeignKey('user.id'))
    duration = db.Column(db.Float, default=0.00, doc='hours')

class User(NamedModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']

    email = db.Column(db.Unicode(32))
    password = db.Column(db.Unicode(128))
    role = db.Column(db.Unicode(32), default='guest')
    worktimes = db.relationship('WorkTime', backref='user')
    assigned_tasks = db.relationship('Task', backref='assignee')

    @property
    def login(self):
        return self.name.lower()

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.role and self.role != 'suspended'

    @property
    def is_anonymous(self):
        return not self.is_authenticated

    def get_id(self):
        return self.id


class Task(NamedModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']

    id = db.Column(db.Unicode, primary_key=True, nullable=False, default=generate_id)

    department = db.Column(db.Unicode(16))
    content = db.Column(db.Unicode(1024))
    created_by = db.Column(db.Unicode(64))
    status = db.Column(db.Unicode(16), default='new')

    worktimes = db.relationship('WorkTime', backref='task')
    followers = db.relationship('User', secondary=followings, backref='followed')

    planned_time = db.Column(db.Float, default=0.00, doc='hours')

    project_id = db.Column(db.Unicode, db.ForeignKey('project.id'))
    order_id = db.Column(db.Unicode, db.ForeignKey('order.id'))
    milestone_id = db.Column(db.Unicode, db.ForeignKey('milestone.id'))

    assignee_id = db.Column(db.Unicode, db.ForeignKey('user.id'))

    parent_id = db.Column(db.Unicode, db.ForeignKey('task.id'))
    parent = db.relationship("Task", remote_side=[id])


def do_delete_pending_objects(session, flush_context, instances=None):  # pylint: disable=unused-argument

    to_be_deleted_object_list = MODELS_GLOBAL_CONTEXT['to_be_deleted_object_list']

    for item in list(to_be_deleted_object_list)[:100]:
        cls, id_ = item
        session.query(cls).filter(cls.id == id_).delete()
        to_be_deleted_object_list.remove(item)


def check_limit_before_insert(mapper, connection, target):  # pylint: disable=unused-argument

    if MODELS_GLOBAL_CONTEXT.get('check_limit_before_insert_disabled'):
        return

    to_be_deleted_object_list = MODELS_GLOBAL_CONTEXT['to_be_deleted_object_list']

    self = target

    exceeding_objects = self.check_size_limit()

    if exceeding_objects:
        logging.warning("exceeding_objects.count():{}".format(exceeding_objects.count()))
        for o in exceeding_objects:
            to_be_deleted_object_list.add((target.__class__, o.id))


def install_listeners():

    db = MODELS_GLOBAL_CONTEXT['db']

    db.event.listen(db.session, 'before_flush', do_delete_pending_objects)

    for cls in scan_for_models().values():
        if cls.row_count_limt > 0:
            db.event.listen(cls, 'before_insert', check_limit_before_insert)


def init_db(app):

    db = MODELS_GLOBAL_CONTEXT['db']
    db.init_app(app)

    install_listeners()

    force_reset = app.config.get('FORCE_RESET_DB')
    db_path = app.config['DATABASE_FILE']
    if not os.path.exists(db_path) or force_reset:
        reset_db(app, db)

    if app.config.get("INSERT_ADMIN_USER_IN_DB"):
        insert_admin_user_in_db(app, db)

    if app.config.get("POPULATE_SAMPLE_DB"):
        populate_sample_db(app, db)

    return db
