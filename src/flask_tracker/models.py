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
import sqlite3
from datetime import datetime

from sqlalchemy.inspection import inspect  # pylint: disable=import-error

from sqlalchemy import event         # pylint: disable=import-error

import iso8601                       # pylint: disable=import-error
import flask_sqlalchemy              # pylint: disable=import-error

from werkzeug.security import generate_password_hash

sqlalchemy_db_ = flask_sqlalchemy.SQLAlchemy()
sqlalchemy_session_ = None

def generate_id():
    return str(uuid.uuid4())

def populate_default_db(app, db):
    
    fixtes = [
        (Customer, {'name': 'Alfa'}),
        (Customer, {'name': 'Comex'}),
        (Project, {'name': 'Thor'}),
        (Project, {'name': 'Desk'}),
        (Project, {'name': 'ColorLab'}),
        (Milestone, {'name': '2020.q1'}),
        (Milestone, {'name': '2020.q2'}),
        (Milestone, {'name': '2020.q2'}),
        (Milestone, {'name': '2020.q3'}),
        (Order, {'name': 'O_001'}),
        (Order, {'name': 'O_002'}),
        (User, {'name': 'admin', 'password': generate_password_hash('admin'), 'email': 'admin@gmail.com'}),
        (User, {'name': 'test', 'password': generate_password_hash('test'), 'email': 'test@gmail.com'}),
    ]

    with app.app_context():
        for klass, args in fixtes:
            try:
                obj = klass(**args)
                db.session.add(obj)
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                logging.info(exc)

def reset_db(app, db, force_reset=False):

    # ~ _dir = os.path.realpath(os.getcwd())
    # ~ database_path = os.path.join(_dir, app.config['DATABASE_FILE'])
    database_path = app.config['DATABASE_FILE']
    
    if not os.path.exists(database_path) or force_reset:
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.commit()

class BaseModel(object):                         # pylint: disable=too-few-public-methods

    row_count_limt = 1000

    date_created = sqlalchemy_db_.Column(sqlalchemy_db_.DateTime, default=datetime.utcnow)
    date_modified = sqlalchemy_db_.Column(sqlalchemy_db_.DateTime, default=datetime.utcnow)
    name = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode(64), nullable=False, unique=True, index=True)

    id = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode, primary_key=True, nullable=False, default=generate_id)
    description = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode(200))

    @classmethod
    def check_size_limit(cls):
        exceeding_objects = []
        if cls.row_count_limt > 0:
            row_count = cls.query.count()
            exceeding = max(0, row_count - cls.row_count_limt)
            if exceeding > 0:
                exceeding += int(cls.row_count_limt * 0.1)  # below watermark
                exceeding_objects = cls.query.order_by(cls.date_created).limit(exceeding)
                msg = "cls:{}, row_count:{}, exceeding:{}, exceeding_objects.count():{}".format(
                    cls, row_count, exceeding, exceeding_objects.count())
                logging.warning(msg)
        return exceeding_objects

    def get_id_short(self):
        return self.id[:8]

    id_short = property(get_id_short)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<{}>{}: {}".format(type(self).__name__[:1], self.id_short, self.__str__())

class Project(BaseModel, sqlalchemy_db_.Model):  # pylint: disable=too-few-public-methods

    milestones = sqlalchemy_db_.relationship('Milestone', backref='project')
    orders = sqlalchemy_db_.relationship('Order', backref='project')

class Customer(BaseModel, sqlalchemy_db_.Model):   # pylint: disable=too-few-public-methods

    orders = sqlalchemy_db_.relationship('Order', backref='customer')

class Order(BaseModel, sqlalchemy_db_.Model):    # pylint: disable=too-few-public-methods

    tasks = sqlalchemy_db_.relationship('Task', backref='order')

    project_id   = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode, sqlalchemy_db_.ForeignKey('project.id'))

    customer_id   = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode, sqlalchemy_db_.ForeignKey('customer.id'))

    def __str__(self):
        customer_name = (self.customer and self.customer.name) or 'none'
        project_name = (self.project and self.project.name) or 'none'
        return "{}:{}.{}".format(project_name, customer_name, self.name)

class Milestone(BaseModel, sqlalchemy_db_.Model):     # pylint: disable=too-few-public-methods

    due_date = sqlalchemy_db_.Column(sqlalchemy_db_.DateTime)

    tasks = sqlalchemy_db_.relationship('Task', backref='milestone')

    project_id   = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode, sqlalchemy_db_.ForeignKey('project.id'))

    def __str__(self):
        prj_name = (self.project and self.project.name) or 'none'
        return "{}.{}".format(prj_name, self.name)


class WorkTime(BaseModel, sqlalchemy_db_.Model):     # pylint: disable=too-few-public-methods

    task_id    = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode, sqlalchemy_db_.ForeignKey('task.id'))
    user_id    = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode, sqlalchemy_db_.ForeignKey('user.id'))

    duration = sqlalchemy_db_.Column(sqlalchemy_db_.Float, default=0.00, doc='hours')

class User(BaseModel, sqlalchemy_db_.Model):     # pylint: disable=too-few-public-methods

    email = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode(32))
    password = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode(128))
    role = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode(32), default='guest')
    worktimes = sqlalchemy_db_.relationship('WorkTime', backref='user')

    tasks = sqlalchemy_db_.relationship('Task', backref='assignee')

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
        return not self.is_authenticated()

    def get_id(self):
        return self.id


class Task(BaseModel, sqlalchemy_db_.Model):     # pylint: disable=too-few-public-methods

    department = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode(64))
    content = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode(1024))
    created_by    = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode(64))

    worktimes = sqlalchemy_db_.relationship('WorkTime', backref='task')

    planned_time = sqlalchemy_db_.Column(sqlalchemy_db_.Float, default=0.00, doc='hours')

    order_id = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode, sqlalchemy_db_.ForeignKey('order.id'))
    milestone_id = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode, sqlalchemy_db_.ForeignKey('milestone.id'))
    user_id = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode, sqlalchemy_db_.ForeignKey('user.id'))

    parent_id = sqlalchemy_db_.Column(sqlalchemy_db_.Unicode, sqlalchemy_db_.ForeignKey('task.id'))
    related_tasks = sqlalchemy_db_.relationship("Task")    
    # ~ parent = sqlalchemy_db_.relationship("Task", remote_side=[id_])
    # ~ children = sqlalchemy_db_.relationship("Task", backref=sqlalchemy_db_.backref('parent', remote_side=[id_]))    
    

def init_db(app):

    global sqlalchemy_session_      # pylint: disable=global-statement
    global sqlalchemy_db_           # pylint: disable=global-statement

    sqlalchemy_db_.init_app(app)

    sqlalchemy_session_ = sqlalchemy_db_.session

    reset_db(app, sqlalchemy_db_, force_reset=False)
    populate_default_db(app, sqlalchemy_db_)

    return sqlalchemy_db_, sqlalchemy_session_
