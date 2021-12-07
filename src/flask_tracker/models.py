# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=broad-except

import os
import uuid
import json
import logging
import traceback
from datetime import datetime

from sqlalchemy.inspection import inspect  # pylint: disable=import-error

import iso8601                       # pylint: disable=import-error

from flask import Markup  # pylint: disable=import-error
from werkzeug.security import generate_password_hash  # pylint: disable=import-error
import flask_sqlalchemy              # pylint: disable=import-error

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

    return MODELS_GLOBAL_CONTEXT['app'].config.get("SAMPLE_TASK_CONTENT", " ** sample task ** ")


def get_default_claim_content():

    return MODELS_GLOBAL_CONTEXT['app'].config.get("SAMPLE_CLAIM_CONTENT", " ** sample claim ** ")


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
            else:
                logging.warning(" name:{}, pwd_:{}, email_:{}, role:{}, cost:{}".format(name, pwd_, email_, role, cost))


def fix_slugify_categoriy_in_tasks(app, db):

    import re

    def slugify(text):
        try:
            import unidecode  # pylint: disable=import-error
            text = unidecode.unidecode(text).lower()
        except ModuleNotFoundError:
            text = text.lower()
        return re.sub(r'[\W_]+', '-', text)

    with app.app_context():

        for t in db.session.query(Task).all():
            try:
                if t.category:
                    category_s = slugify(t.category)
                    logging.warning("t:'{}' t.category:{}, category_s:{}".format(t.name, t.category, category_s))
                    t.category = category_s
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                logging.warning(exc)


def fix_missing_number_in_tasks(app, db):

    with app.app_context():

        t = db.session.query(Task).order_by(Task.number.desc()).first()
        N = t.number + 1 if t.number is not None else 1

        for t in db.session.query(Task).filter(not Task.number):

            try:
                if not t.number:
                    t.number = N
                    N += 1
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                logging.warning(exc)


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
        categories = [s for s, S in MODELS_GLOBAL_CONTEXT['app'].config.get("TASK_categORIES", [])]
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
                'category': random.choice(categories),
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

    logging.warning("resetting db (dropping all tables)")

    with app.app_context():
        db.drop_all()
        db.session.commit()


followings = sqlalchemy_db_.Table(
    'followings',
    sqlalchemy_db_.Column(
        'user_id',
        sqlalchemy_db_.Unicode,
        sqlalchemy_db_.ForeignKey('user.id'),
        primary_key=True),
    sqlalchemy_db_.Column(
        'task_id',
        sqlalchemy_db_.Unicode,
        sqlalchemy_db_.ForeignKey('task.id'),
        primary_key=True))

claimings = sqlalchemy_db_.Table(
    'claimings',
    sqlalchemy_db_.Column(
        'user_id',
        sqlalchemy_db_.Unicode,
        sqlalchemy_db_.ForeignKey('user.id'),
        primary_key=True),
    sqlalchemy_db_.Column(
        'claim_id',
        sqlalchemy_db_.Unicode,
        sqlalchemy_db_.ForeignKey('claim.id'),
        primary_key=True))


class BaseModel(object):                         # pylint: disable=too-few-public-methods

    row_count_limt = 100 * 1000

    db = MODELS_GLOBAL_CONTEXT['db']

    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_modified = db.Column(db.DateTime, default=datetime.utcnow)

    id = db.Column(db.Unicode, primary_key=True, nullable=False, default=generate_id)
    description = db.Column(db.Unicode())

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
        return self.id[:4].upper()

    id_short = property(get_id_short)

    def object_to_json(self, indent=2):
        data = self.object_to_dict()
        return json.dumps(data, indent=indent)

    def object_to_dict(self):

        data = {c.key: getattr(self, c.key)
                for c in inspect(self).mapper.column_attrs}
        # ~ for c in inspect(self).mapper.column_attrs if getattr(self, c.key) is not None}

        for k in data.keys():
            if isinstance(data[k], datetime):
                data[k] = data[k].isoformat()

        return data

    @classmethod
    def object_from_json(cls, json_data):

        data = json.loads(json_data)
        obj = cls.object_from_dict(data)
        return obj

    @classmethod
    def object_from_dict(cls, data_dict):

        data_dict_cpy = {k: v for k, v in data_dict.items() if v is not None}
        for k in data_dict_cpy:
            if 'date' in k and isinstance(data_dict_cpy[k], str):
                data_dict_cpy[k] = iso8601.parse_date(data_dict_cpy[k])

        obj = cls(**data_dict_cpy)

        return obj


class NamedModel(BaseModel):

    db = MODELS_GLOBAL_CONTEXT['db']

    name = db.Column(db.Unicode(64), nullable=False, unique=True, index=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        # ~ return "<{}>{}: {}".format(type(self).__name__[:1], self.id_short, self.__str__())
        return self.__str__()


class Project(NamedModel, sqlalchemy_Model):  # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    milestones = db.relationship('Milestone', backref='project')


class Customer(NamedModel, sqlalchemy_Model):   # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    orders = db.relationship('Order', backref='customer')
    claims = db.relationship('Claim', backref='customer')
    improvements = db.relationship('Improvement', backref='customer')


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
    cost_per_hour = db.Column(db.Float, default=0.00, doc='cost per hour in arbitrary unit')

    worktimes = db.relationship('WorkTime', backref='user')

    assigned_tasks = db.relationship('Task', backref='assignee')

    assigned_claims = db.relationship('Claim', backref='owner')

    modifications = db.relationship('History', backref='user')

    authored_improvements = db.relationship('Improvement', primaryjoin="User.id==Improvement.author_id", backref='author')
    assigned_improvements = db.relationship('Improvement', primaryjoin="User.id==Improvement.assignee_id", backref='assignee')
    notified_improvements = db.relationship('Improvement', primaryjoin="User.id==Improvement.notifier_id", backref='notifier')

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

    @property
    def is_admin(self):
        return self.role == 'admin'

    def get_id(self):
        return self.id


class Attachment(NamedModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    attached_id = db.Column(db.Unicode, db.ForeignKey('task.id'))
    claimed_id = db.Column(db.Unicode, db.ForeignKey('claim.id'))


class History(BaseModel, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']
    user_id = db.Column(db.Unicode, db.ForeignKey('user.id'))

    task_id = db.Column(db.Unicode, db.ForeignKey('task.id'))
    claim_id = db.Column(db.Unicode, db.ForeignKey('claim.id'))


class ItemBase(NamedModel):     # pylint: disable=too-few-public-methods

    content_max_len = 5 * 1024

    db = MODELS_GLOBAL_CONTEXT['db']

    name = db.Column(db.Unicode(64), nullable=False)

    department = db.Column(db.Unicode(16))
    created_by = db.Column(db.Unicode(64))
    status = db.Column(db.Unicode(16), default='new')
    priority = db.Column(db.Unicode(16), default='low')

    # ~ to be overridden by inheriting class
    attachments = []

    @property
    def formatted_attach_names(self):
        ret = [Markup(a.name) for a in self.attachments]
        return ret

    @formatted_attach_names.setter
    def formatted_attach_names(self, val):
        pass


class Task(ItemBase, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']

    id = db.Column(db.Unicode, primary_key=True, nullable=False, default=generate_id)

    content = db.Column(db.Unicode(ItemBase.content_max_len), default=get_default_task_content)

    category = db.Column(db.Unicode(16), default='')
    planned_time = db.Column(db.Float, default=0.00, doc='hours')

    order_id = db.Column(db.Unicode, db.ForeignKey('order.id'))
    milestone_id = db.Column(db.Unicode, db.ForeignKey('milestone.id'))
    assignee_id = db.Column(db.Unicode, db.ForeignKey('user.id'))

    parent_id = db.Column(db.Unicode, db.ForeignKey('task.id'))
    parent = db.relationship("Task", remote_side=[id])

    worktimes = db.relationship('WorkTime', backref='task')

    attachments = db.relationship('Attachment', backref='attached')
    modifications = db.relationship('History', backref='task')
    followers = db.relationship('User', secondary=followings, backref='followed')


class Claim(ItemBase, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    db = MODELS_GLOBAL_CONTEXT['db']

    id = db.Column(db.Unicode, primary_key=True, nullable=False, default=generate_id)

    content = db.Column(db.Unicode(5 * 1024), default=get_default_claim_content)

    contact = db.Column(db.Unicode())  # : (mail)
    machine_model = db.Column(db.Unicode(64))
    serial_number = db.Column(db.Unicode(64))
    installation_date = db.Column(db.DateTime, default=datetime.utcnow)
    installation_place = db.Column(db.Unicode(64))
    # (menù tendina: gruppo colorante, gruppo base, EV colorante, EV base, Autocap, umidificatore, parti elettroniche, altre parti meccaniche)
    damaged_group = db.Column(db.Unicode(64))
    quantity = db.Column(db.Integer)
    serial_number_of_damaged_part = db.Column(db.Unicode(64))
    the_part_have_been_requested = db.Column(db.Boolean)  # (menù tendina: si, no)
    is_covered_by_warranty = db.Column(db.Boolean)  # (menù tendina: si, no)

    customer_id = db.Column(db.Unicode, db.ForeignKey('customer.id'))
    owner_id = db.Column(db.Unicode, db.ForeignKey('user.id'))

    attachments = db.relationship('Attachment', backref='claimed')
    modifications = db.relationship('History', backref='claim')
    followers = db.relationship('User', secondary=claimings, backref='claimed')


class Improvement(ItemBase, sqlalchemy_Model):     # pylint: disable=too-few-public-methods

    row_count_limt = 1000

    db = MODELS_GLOBAL_CONTEXT['db']

    machine_model = db.Column(db.Unicode(64))
    due_date = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.Column(db.Unicode(), default='')
    assembly_subgroup = db.Column(db.Unicode(), default='')
    component = db.Column(db.Unicode(), default='')
    market_potential = db.Column(db.Unicode(), default='')
    target_department = db.Column(db.Unicode(), default='')

    content = db.Column(db.Unicode(5 * 1024), default='')
    estimated_resources = db.Column(db.Unicode(), default='')
    estimated_time_steps = db.Column(db.Unicode(), default='')
    notes = db.Column(db.Unicode(), default='')

    customer_id = db.Column(db.Unicode, db.ForeignKey('customer.id'))

    author_id = db.Column(db.Unicode, db.ForeignKey('user.id'))
    assignee_id = db.Column(db.Unicode, db.ForeignKey('user.id'))
    notifier_id = db.Column(db.Unicode, db.ForeignKey('user.id'))


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

    with app.app_context():
        # ~ History.__table__.drop(db.engine)
        db.create_all()
        db.session.commit()

    install_listeners()

    return db
