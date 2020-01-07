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

from werkzeug.security import generate_password_hash  # pylint: disable=import-error
import flask_sqlalchemy              # pylint: disable=import-error

from flask import Markup  # pylint: disable=import-error

sqlalchemy_db_ = flask_sqlalchemy.SQLAlchemy()
sqlalchemy_session_ = None
sqlalchemy_Model = sqlalchemy_db_.Model

MODELS_GLOBAL_CONTEXT = {
    'db': sqlalchemy_db_,
    'session': sqlalchemy_db_.session,
    'to_be_deleted_object_list': set([]),
    'table_name2model_classes_map': {},
    'package_version': None,
    'app': None}


def get_package_version():

    if MODELS_GLOBAL_CONTEXT.get('package_version'):
        return MODELS_GLOBAL_CONTEXT['package_version']

    import subprocess
    import sys

    ver = '0.0.0'
    try:
        pth = os.path.abspath(os.path.dirname(sys.executable))
        # ~ logging.warning("pth:{}".format(pth))
        cmd_ = '{}/pip show flask_tracker'.format(pth)
        # ~ logging.warning("cmd_:{}".format(cmd_))
        for line in subprocess.run(cmd_.split(), stdout=subprocess.PIPE).stdout.decode().split('\n'):
            # ~ logging.warning("line:{}".format(line))
            if 'Version' in line:
                ver = line.split(":")[1]
                ver = ver.strip()
    except Exception as exc:  # pylint: disable=broad-except
        logging.error(exc)

    MODELS_GLOBAL_CONTEXT['package_version'] = ver

    return ver


def get_models_map():

    t2m_map = MODELS_GLOBAL_CONTEXT['table_name2model_classes_map']

    if t2m_map is None:
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

    return MODELS_GLOBAL_CONTEXT['table_name2model_classes_map']


def get_default_task_content():

    return MODELS_GLOBAL_CONTEXT['app'].config.get("SAMPLE_TASK_CONTENT", " *** ")


def generate_id():
    return str(uuid.uuid4())


def insert_users_in_db(app, db):

    with app.app_context():

        for name, pwd_, email_, role, cost in app.config.get("USERS"):

            args = {'name': name,
                    'password': generate_password_hash(pwd_),
                    'role': role,
                    'cost_per_hour': cost,
                    'email': email_}

            try:
                obj = User(**args)
                db.session.add(obj)
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                logging.info(exc)


def populate_sample_db(app, db, N):   # pylint: disable=too-many-locals

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
        (Order, {'name': 'O_0010', 'amount': 100}),
        (Order, {'name': 'O_0011', 'amount': 50}),
        (Order, {'name': 'O_0020', 'amount': 100}),
    ]

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

        import random

        priorities = [s for s, S in MODELS_GLOBAL_CONTEXT['app'].config.get("TASK_PRIORITIES", [])]
        cathegories = [s for s, S in MODELS_GLOBAL_CONTEXT['app'].config.get("TASK_CATHEGORIES", [])]
        sts_ = [s for s, S in MODELS_GLOBAL_CONTEXT['app'].config.get("TASK_STATUSES", [])]
        tags = ['fattibilita', 'pianificazione', 'design', 'prototipo', 'preserie']
        users = [u for u in db.session.query(User).all()]
        projects = [u for u in db.session.query(Project).all()]
        orders = [u for u in db.session.query(Order).all()]
        milestones = [u for u in db.session.query(Milestone).all()]
        # ~ logging.warning("priorities:{}".format( priorities))
        # ~ logging.warning("sts_      :{}".format(sts_      ))
        # ~ logging.warning("users:{}".format(users))
        for i in range(N):
            dscrs = ', '.join((random.choice(tags), random.choice(tags), random.choice(tags)))
            pars = {
                'name': 'Task_%03d' % i,
                'priority': random.choice(priorities),
                'cathegory': random.choice(cathegories),
                'status': random.choice(sts_),
                'assignee': users[i % len(users)],
                'project': projects[i % len(projects)],
                'milestone': milestones[i % len(milestones)],
                'order': orders[i % len(orders)],
                'description': dscrs,
            }
            try:
                t = Task(**pars)
                db.session.add(t)
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                logging.warning(exc)
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
    milestones = db.relationship('Milestone', backref='project')


class Customer(NamedModel, sqlalchemy_Model):   # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    orders = db.relationship('Order', backref='customer')


class Order(NamedModel, sqlalchemy_Model):    # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    tasks = db.relationship('Task', backref='order')
    customer_id = db.Column(db.Unicode, db.ForeignKey('customer.id'))

    amount = db.Column(db.Float, default=0.00, doc='economic amount of the order in arbitrary unit')

    def __str__(self):
        customer_name = (self.customer.name if self.customer else 'none')
        return "{}.{}".format(customer_name, self.name)

    @property
    def in_progress(self):
        return len([t for t in self.tasks if t.status == 'in_progress']) > 0


class Milestone(NamedModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    start_date = db.Column(db.Date, default=datetime.utcnow)
    due_date = db.Column(db.Date, default=datetime.utcnow)
    tasks = db.relationship('Task', backref='milestone')

    project_id = db.Column(db.Unicode, db.ForeignKey('project.id'))

    name = db.Column(db.Unicode(64), nullable=False)
    sqlalchemy_db_.UniqueConstraint('name', 'project_id')

    @property
    def in_progress(self):
        return len([t for t in self.tasks if t.status == 'in_progress']) > 0

    def __str__(self):
        return Markup("{}.{}".format(self.project, self.name))


class WorkTime(BaseModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    task_id = db.Column(db.Unicode, db.ForeignKey('task.id'))
    user_id = db.Column(db.Unicode, db.ForeignKey('user.id'))
    duration = db.Column(db.Float, default=0.00, doc='hours')


class User(NamedModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']

    email = db.Column(db.Unicode(64))
    password = db.Column(db.Unicode(128))
    role = db.Column(db.Unicode(32), default='guest')
    worktimes = db.relationship('WorkTime', backref='user')
    assigned_tasks = db.relationship('Task', backref='assignee')
    cost_per_hour = db.Column(db.Float, default=0.00, doc='cost per hour in arbitrary unit')

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


class Attachment(NamedModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']

    attached_id = db.Column(db.Unicode, db.ForeignKey('task.id'))


class Task(NamedModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']

    id = db.Column(db.Unicode, primary_key=True, nullable=False, default=generate_id)

    content = db.Column(db.Unicode(1024), default=get_default_task_content)

    department = db.Column(db.Unicode(16))
    created_by = db.Column(db.Unicode(64))
    status = db.Column(db.Unicode(16), default='new')
    priority = db.Column(db.Unicode(16), default='low')
    cathegory = db.Column(db.Unicode(16), default='')
    planned_time = db.Column(db.Float, default=0.00, doc='hours')

    worktimes = db.relationship('WorkTime', backref='task')
    attachments = db.relationship('Attachment', backref='attached')

    followers = db.relationship('User', secondary=followings, backref='followed')

    order_id = db.Column(db.Unicode, db.ForeignKey('order.id'))
    milestone_id = db.Column(db.Unicode, db.ForeignKey('milestone.id'))
    assignee_id = db.Column(db.Unicode, db.ForeignKey('user.id'))

    parent_id = db.Column(db.Unicode, db.ForeignKey('task.id'))
    parent = db.relationship("Task", remote_side=[id])

    @property
    def formatted_attach_names(self):
        return [Markup(a.name) for a in self.attachments]

    @formatted_attach_names.setter
    def formatted_attach_names(self, val):
        pass


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

    exceeding_objects = target.check_size_limit()

    if exceeding_objects:
        logging.warning("exceeding_objects.count():{}".format(exceeding_objects.count()))
        for o in exceeding_objects:
            to_be_deleted_object_list.add((target.__class__, o.id))


def install_listeners():

    db = MODELS_GLOBAL_CONTEXT['db']

    db.event.listen(db.session, 'before_flush', do_delete_pending_objects)

    for cls in get_models_map().values():
        if cls.row_count_limt > 0:
            db.event.listen(cls, 'before_insert', check_limit_before_insert)


def setup_orm(app):

    db = MODELS_GLOBAL_CONTEXT['db']

    p_ver = get_package_version().split('.')
    p_ver_maj = p_ver[1]

    force_reset = app.config.get('FORCE_RESET_DB')
    db_path = app.config.get('DATABASE_FILE')
    db_ver = os.path.basename(db_path).split('.')[1]

    assert db_ver == "v{}".format(p_ver_maj), "db version:{} is not supported by release:{}".format(db_ver, p_ver)

    db_base_path = os.path.dirname(db_path)
    if not os.path.exists(db_base_path):
        os.makedirs(db_base_path)

    if not db_path or not os.path.exists(db_path) or force_reset:
        reset_db(app, db)
    if app.config.get("INSERT_USERS_IN_DB"):
        insert_users_in_db(app, db)
    if app.config.get("POPULATE_SAMPLE_DB"):
        populate_sample_db(app, db, app.config.get("POPULATE_SAMPLE_DB"))


def init_orm(app):

    MODELS_GLOBAL_CONTEXT['app'] = app
    db = MODELS_GLOBAL_CONTEXT['db']

    db.init_app(app)

    setup_orm(app)

    install_listeners()

    return db
