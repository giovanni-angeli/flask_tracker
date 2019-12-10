# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=broad-except

import os
import time
import logging
import traceback
import json
import tempfile

from datetime import datetime

from flask import (Markup, url_for, redirect, request, flash, render_template, Response, abort)  # pylint: disable=import-error
# ~ from flask import Flask, url_for, redirect, render_template, request

from werkzeug.security import generate_password_hash, check_password_hash

from wtforms import form, fields, validators

from jinja2 import contextfunction

import flask_admin  # pylint: disable=import-error
import flask_login  # pylint: disable=import-error
from flask_admin.base import MenuLink, Admin     # pylint: disable=import-error
from flask_admin.contrib.sqla import ModelView  # pylint: disable=import-error

import markdown2

from flask_tracker.models import (
        Task,
        Project,
        Milestone,
        Customer,
        Order, 
        User, 
    )

DEPARTMENTS = [
    ('SW', 'SW'), 
    ('FW', 'FW'), 
    ('mechanical', 'Mechanical'), 
    ('electronics', 'Electronics'), 
    ('lab', 'Lab'),
]

ROLES_CAPABILITIES_MAP = {
    'admin': {'default': 'crud'}, 
    'project_admin': {
        'default': 'r',
        'user': 'crud',
        'task': 'crud',
        'project': 'crud',
        'milestone': 'crud',
        'order': 'r',
        'customer': 'r',
    }, 
    'task_admin': {
        'default': 'r',
        'user': 'r',
        'task': 'crud',
        'project': 'r',
        'milestone': 'r',
        'order': 'r',
        'customer': 'r',
    }, 
    'guest': {'default': 'r'}, 
    'suspended': {'default': ''}, 
}

_db_session = None

class TrackerModelView(ModelView):

    can_view_details = True
    can_export = True
    export_max_rows = 1000
    export_types = ['csv', 'xls', 'json']

    details_template = "admin/details.html"
    list_template = 'admin/list.html'
    create_template = 'admin/create.html'
    edit_template = 'admin/edit.html'

    def has_capabilities(self, role, table_name, operation='r'):

        ret = False
        cap = ROLES_CAPABILITIES_MAP[role].get(table_name)
        if not cap:
            cap = ROLES_CAPABILITIES_MAP[role].get('default')
        if operation in cap:
            ret = True

        logging.warning("role:{}, table_name:{}, operation:{}, ret:{}".format(role, table_name, operation, ret))

        return ret

    def on_model_change(self, form, obj, is_created):
        ret = super().on_model_change(form, obj, is_created)
        return ret

    def is_accessible(self):

        ret = False
        if flask_login.current_user.is_authenticated:
            if self.has_capabilities(flask_login.current_user.role, self.model.__tablename__):
                ret = True
        return ret


class OrderView(TrackerModelView):

    column_editable_list = (
        'customer',
        'project',
    )

class MilestoneView(TrackerModelView):

    column_editable_list = (
        'project',
        # ~ 'due_date',
    )

class ProjectView(TrackerModelView):

    column_editable_list = (
        'milestones',
        'orders',
    )

    column_list = (
        'name',
        'milestones',
        'orders',
    )

class UserView(TrackerModelView):

    form_choices = {
        'role': [(k, k) for k in ROLES_CAPABILITIES_MAP.keys()],
    }

    column_list = (
        'name',
        'email',
        'role',
        'worktimes',
        'assigned_tasks',
    )

    column_details_exclude_list = (
        'password',
    )

    form_excluded_columns = (
        'date_created',
        'date_modified',
        'password',
        'worktimes',
        'assigned_tasks',
    )

class TaskView(TrackerModelView):

    # ~ edit_template = 'admin/task_edit.html'
    # ~ edit_template = 'task_editor_page.html'

    can_delete = False

    form_args = {
        'content': {
            'label': 'content',
        },
    }

    form_choices = {
        'department': DEPARTMENTS,
    }

    form_widget_args = {
    }

    column_list = (
        'name',
        'milestone',
        'order',
        'related_tasks',
        'assignee',
        'worktimes',
    )

    column_editable_list = (
        # ~ 'planned_hours',
        # ~ 'spent_hours',
        # ~ 'parent_id',
        # ~ 'parent.name',
        # ~ 'assignee_id',
        'related_tasks',
    )

    column_filters = (
        'name',
        'date_modified',
        'description',
        'order.name',
        'order.customer',
        'milestone.project',
        'milestone.name',
        # ~ 'product.brand',
    )

    form_columns = (
        'name',
        'description',
        'department',
        'milestone',
        'order',
        'related_tasks',
        'assignee',
        'content',
    )

    # ~ form_excluded_columns = (
        # ~ 'date_created',
        # ~ 'date_modified',
        # ~ 'created_by',
        # ~ 'worktimes',
        # ~ 'content',
    # ~ )

    def get_edit_form(self):
        form = super(TaskView, self).get_edit_form()
        form.content = fields.TextAreaField(u'* content *', [validators.optional(), validators.length(max=5000)], render_kw={'rows': '20'})
        form.preview_content = fields.BooleanField(u'* preview content *', [], render_kw={})
        return form

    @contextfunction
    def get_detail_value(self, context, model, name):
        ret = super().get_detail_value(context, model, name)
        if name == 'content':
            ret = markdown2.markdown(ret)
            ret = Markup(ret)
        return ret


class TrackerAdminResources(flask_admin.AdminIndexView):

    @flask_admin.expose("/")
    @flask_admin.expose("/home")
    @flask_admin.expose("/index")
    def index(self, ):

        if not flask_login.current_user.is_authenticated:
            return redirect(url_for('.login'))

        logging.warning("self._template:{}".format(self._template))
        ctx = {
        }
        return self.render(self._template, **ctx)

    @flask_admin.expose('/login/', methods=('GET', 'POST'))
    def login(self):

        logging.warning("")

        # handle user login
        form = LoginForm(request.form)

        logging.warning("form:{}".format(form))

        if flask_admin.helpers.validate_form_on_submit(form):
            user = form.get_user()
            flask_login.login_user(user)
            logging.warning("user.name:{}".format(user.name))

        logging.warning("login.current_user:{}".format(flask_login.current_user))

        if flask_login.current_user.is_authenticated:
            return redirect(url_for('.index'))

        self._template_args['form'] = form

        return super(TrackerAdminResources, self).index()


    @flask_admin.expose('/logout/')
    def logout(self):
        flask_login.logout_user()
        return redirect(url_for('.index'))


# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        
        logging.warning("self.login.data:{}".format(self.login.data))
        
        user = self.get_user()

        logging.warning("user:{}".format(user))

        if user is None:
            raise validators.ValidationError('Invalid user')

        # we're comparing the plaintext pw with the the hash from the db
        if not check_password_hash(user.password, self.password.data):
        # to compare plain text passwords use
        # if user.password != self.password.data:
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        global _db_session
        return _db_session.query(User).filter_by(name=self.login.data).first()


def init_admin(app, db):

    global _db_session
    _db_session = db.session

    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        logging.warning("user_id:{}".format(user_id))
        return _db_session.query(User).get(user_id)

    index_view_ = TrackerAdminResources(url='/')
    index_view_.app = app

    admin_ = Admin(app, name='FlaskTracker', template_mode='bootstrap3', index_view=index_view_)

    admin_.add_view(TaskView(Task, db.session))
    admin_.add_view(ProjectView(Project, db.session))
    admin_.add_view(MilestoneView(Milestone, db.session))
    admin_.add_view(OrderView(Order, db.session))
    admin_.add_view(TrackerModelView(Customer, db.session, category="admin"))
    admin_.add_view(UserView(User, db.session, category="admin"))

    return admin_
