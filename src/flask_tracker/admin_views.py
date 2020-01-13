# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=broad-except

import os
import logging
import traceback
import json
import time
import difflib
import urllib.parse
from datetime import datetime, timezone, timedelta

import markdown  # pylint: disable=import-error
from werkzeug import secure_filename  # pylint: disable=import-error, no-name-in-module
from jinja2 import contextfunction   # pylint: disable=import-error
from flask import (Markup)  # pylint: disable=import-error
from wtforms import (form, fields, validators)  # pylint: disable=import-error
import flask_login  # pylint: disable=import-error
from flask_admin.contrib.sqla import ModelView  # pylint: disable=import-error
from flask_admin.form.widgets import DatePickerWidget  # pylint: disable=import-error

from flask_tracker.models import (User, History, MODELS_GLOBAL_CONTEXT)


def _handle_task_modification(form_, tsk_as_dict):     # pylint: disable=no-self-use

    modifications = []
    deflt_ = form_.data.get('list_form_pk') is not None
    for k in form_.data.keys():
        if k == 'list_form_pk':
            continue
        if k == 'preview_content_button':
            continue
        a = form_.data[k]
        b = form_[k].object_data

        if isinstance(a, list) and isinstance(a, list):
            a.sort(key=lambda x: x.name)
            b.sort(key=lambda x: x.name)

        if a != b:
            if k == 'content':
                b = difflib.unified_diff(a.split('\n'), b.split('\n'), n=2,
                                         fromfile='before', tofile='after', fromfiledate=time.asctime())
                b = Markup("<br/>".join(b))
            elif deflt_:
                b = " --> {}".format(a)
            else:
                b = "{} --> {}".format(b, a)
            modifications.append((k, str(b)))

    if modifications:

        session = MODELS_GLOBAL_CONTEXT['session']
        args = {
            'task_id': tsk_as_dict['id'],
            'user_id': flask_login.current_user.id,
            'description': json.dumps(modifications, indent=2)
        }
        logging.warning(json.dumps(args, indent=2))
        session.add(History(**args))


def _display_tasks_as_links(cls, context, obj, name):   # pylint: disable=unused-argument

    tasks = getattr(obj, name)
    ret = tasks
    try:
        FMT = '<a href="/task/details/?id={}">{}</a>'
        html_ = ', '.join([FMT.format(t.id, t.id_short or 0) for t in tasks])
        ret = Markup(html_)
    except BaseException:
        logging.warning(traceback.format_exc())
    return ret


def define_view_classes(current_app):
    """
    we define the ModelView classes inside a function, because
    we want an already initialized app to access the app.config.
    """

    class TrackerModelView(ModelView):    # pylint: disable=unused-variable

        named_filter_urls = True

        can_view_details = True
        can_export = True
        export_max_rows = 1000
        export_types = ['csv', 'xls', 'json']

        details_template = "admin/details.html"
        list_template = 'admin/list.html'
        create_template = 'admin/create.html'
        edit_template = 'admin/edit.html'

        column_default_sort = ('date_created', True)

        column_searchable_list = (
            # ~ 'name',
            'description',
        )

        def display_time_to_local_tz(self, context, obj, name):   # pylint: disable=unused-argument,no-self-use
            value = getattr(obj, name)
            value = value.replace(tzinfo=timezone.utc).astimezone().strftime("%d %b %Y (%I:%M:%S %p)")
            return Markup(value)

        column_formatters = {
            'date_created': display_time_to_local_tz,
            'date_modified': display_time_to_local_tz,
        }

        @staticmethod
        def has_capabilities(user, table_name, operation='*'):

            role = user.role
            capabilities_map = current_app.config.get('ROLES_CAPABILITIES_MAP', {})
            default_cap = capabilities_map[role].get('default')
            cap = capabilities_map[role].get(table_name, default_cap)

            # ~ logging.warning("role:{}, table_name:{}, operation:{}, cap:{}".format(role, table_name, operation, cap))

            return operation in cap

        def is_accessible(self):

            ret = False
            if flask_login.current_user.is_authenticated:
                if self.has_capabilities(flask_login.current_user, self.model.__tablename__):
                    ret = True
            return ret

        def on_model_change(self, form_, obj, is_created):
            obj.date_modified = datetime.utcnow()
            ret = super(TrackerModelView, self).on_model_change(form_, obj, is_created)
            return ret

        # ~ def update_model(self, form_, obj):
            # ~ return super().update_model(form_, obj)

    class WorkTimeView(TrackerModelView):  # pylint: disable=unused-variable

        # ~ create_modal = True
        # ~ edit_modal = True
        can_edit = False

        column_list = (
            'date_created',
            'description',
            'duration',
            'user',
            'task',
        )

        column_labels = dict(date_created='Date')

        form_excluded_columns = (
            # ~ 'date_created',
            'date_modified',
        )

        form_args = {
            'date_created': {
                'label': 'date',
            },
        }

        column_filters = (
            'date_created',
            'description',
            'user.name',
            'task.name',
            'task',
        )

        def get_edit_form(self):

            form_ = super().get_edit_form()
            form_.description = fields.TextAreaField('* description *', [validators.optional(), validators.length(max=200)],
                                                     render_kw={'rows': '4'})

            return form_

        def on_model_change(self, form_, obj, is_created):

            ret = super(WorkTimeView, self).on_model_change(form, obj, is_created)
            return ret

    class OrderView(TrackerModelView):    # pylint: disable=unused-variable

        column_editable_list = (
            'customer',
            # ~ 'project',
        )

        column_list = (
            'customer',
            'amount',
            'date_created',
            'description',
            'tasks',
        )

        column_formatters = {
            'tasks': _display_tasks_as_links,
        }

    class MilestoneView(TrackerModelView):   # pylint: disable=unused-variable

        column_editable_list = (
            # ~ 'project',
            'name',
            'project',
            'start_date',
            'due_date',
        )

        column_filters = (
            'start_date',
            'due_date',
            'tasks',
            'project.name',
        )

        column_list = (
            'project',
            'name',
            'start_date',
            'due_date',
            'tasks',
        )

        column_formatters = {
            'tasks': _display_tasks_as_links,
        }

        def get_edit_form(self):

            form_ = super().get_edit_form()

            form_.due_date = fields.DateField('* due date', [], widget=DatePickerWidget(), render_kw={})
            form_.start_date = fields.DateField('* start date', [], widget=DatePickerWidget(), render_kw={})

            return form_

    class ProjectView(TrackerModelView):      # pylint: disable=unused-variable

        column_editable_list = (
            # ~ 'milestones',
            # ~ 'orders',
        )

        column_list = (
            'name',
            'description',
        )

    class UserView(TrackerModelView):     # pylint: disable=unused-variable

        can_create = False
        can_delete = False

        column_labels = dict(followed='Followed Tasks')

        form_args = {
            'email': {
                'validators': [validators.Email()],
            },
            'followed': {
                'label': 'Followed Tasks',
            },
        }

        form_choices = {
            'role': [(k, k) for k in current_app.config.get('ROLES_CAPABILITIES_MAP', {})],
        }

        column_list = (
            'name',
            'email',
            'role',
            'worktimes',
            'assigned_tasks',
            'followed',
        )

        column_editable_list = (
            # ~ 'followed',
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
            'modifications',
        )

        def display_worked_hours(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use

            # ~ session = MODELS_GLOBAL_CONTEXT['session']
            # ~ logged_users = session.query(User).filter(User.is_authenticated).all()

            today = datetime.now()
            start_of_the_week = today - timedelta(days=today.weekday())

            total = sum([h.duration for h in obj.worktimes if h.date_created >= start_of_the_week])
            return Markup("%.2f" % total)

        column_formatters = TrackerModelView.column_formatters.copy()

        column_formatters.update({
            'worktimes': display_worked_hours,
            'assigned_tasks': _display_tasks_as_links,
            'followed': _display_tasks_as_links,
        })

        column_labels = dict(worktimes='Worked Hours in This Week')

    class TaskView(TrackerModelView):     # pylint: disable=unused-variable

        # ~ edit_template = 'admin/edit_task.html'

        # ~ can_delete = False
        # ~ column_details_list = ()

        column_searchable_list = (
            'id',
            'name',
            'description',
            'category',
        )

        form_args = {
            'category': {
                'description': current_app.config.get('CATEGORY_DESCRIPTION', 'missing description.'),
            },
        }

        form_choices = {
            'department': current_app.config.get('DEPARTMENTS'),
            'status': current_app.config.get('TASK_STATUSES'),
            'priority': current_app.config.get('TASK_PRIORITIES'),
            'category': current_app.config.get('TASK_CATEGORIES'),
        }

        column_list = (
            'milestone',
            'id_short',
            'name',
            'description',
            'assignee',
            'status',
            'category',
            'department',
            'order',
            'priority',
            'parent',
            'date_created',
            'followers',
            'worktimes',
        )

        column_details_list = (
            'milestone',
            'id_short',
            'name',
            'description',
            'content',
            'assignee',
            'status',
            'category',
            'department',
            'order',
            'priority',
            'parent',
            'followers',
            'worktimes',
            'date_created',
            'date_modified',
        )

        column_editable_list = (
            'assignee',
            'category',
            'priority',
            'followers',
            'status',
        )

        column_filters = (
            'name',
            'status',
            'date_modified',
            'description',
            'department',
            'category',
            'assignee.name',
            # ~ 'project.name',
            'milestone.name',
            'milestone.project',
            'order.name',
        )

        form_columns = (
            'name',
            'description',
            'assignee',
            'status',
            'priority',
            'category',
            # ~ 'project',
            'department',
            'milestone',
            'order',
            'parent',
            'assignee',
            'followers',
            # ~ 'attachments',
            # ~ 'content',
        )

        column_labels = dict(worktimes='Total Worked Hours', id_short="#")

        def display_worktimes(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use
            """
            /worktime/?flt2_task_name_equals==import%20machine-data%20-%20alfa40
            /worktime/?flt2_task_task_name_equals=UI+page+per+raccolta+dati+volume%2Fpeso
            /worktime/?flt1_task_task_name_contains=UI+page+per+raccolta+dati+volume%2Fpeso

            worktime/?flt2_task_task_name_equals=import%20machine-data%20-%20alfa40
            worktime/?flt2_task_task_name_equals=import+machine-data+-+alfa40
            """

            total = sum([h.duration for h in obj.worktimes])
            ret = total

            try:
                html_ = '<a href="/worktime/?flt2_task_task_name_equals={}" title="show worked hrs details.">{}</a>'.format(
                    urllib.parse.quote_plus(obj.name), total)
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        def display_id_short(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use
            """
            /history/?flt0_task_task_name_equals=Omologazione+prodotti+%2B+tagli+per+riproduzione+basi+intermedie


            """
            value = getattr(obj, name)
            ret = value
            try:
                html_ = '<a href="/history/?flt0_task_task_name_equals={}" title="show history">{}</a>'.format(
                    urllib.parse.quote_plus(obj.name), value)
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        def display_milestone(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use

            value = getattr(obj, name)
            ret = value
            try:
                html_ = '<a href="/milestone/details/?id={}" title="show milestone">{}</a>'.format(
                    obj.milestone_id, value)
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        column_formatters = TrackerModelView.column_formatters.copy()

        column_formatters.update({
            'id_short': display_id_short,
            'milestone': display_milestone,
            'worktimes': display_worktimes,
        })

        def get_edit_form(self):

            form_ = super().get_edit_form()

            form_.formatted_attach_names = fields.TextAreaField(
                'attachment urls', render_kw=dict(value="*", disabled=True))

            cnt_description = Markup(
                'NOTE: you can use <a target="blank_" href="https://daringfireball.net/projects/markdown/syntax">Markdown syntax</a>. Use preview button to see what you get.')

            form_.content = fields.TextAreaField('content', [validators.optional(), validators.length(max=1000)],
                                                 description=cnt_description,
                                                 render_kw={"style": "background:#fff; border:dashed #DD3333 1px; height:480px;"})

            form_.preview_content_button = fields.BooleanField(u'preview content', [], render_kw={})

            return form_

        @contextfunction
        def get_detail_value(self, context, model, name):
            ret = super().get_detail_value(context, model, name)
            if name == 'content':
                ret = markdown.markdown(ret)
                ret = Markup(ret)
            elif name == 'attachments':
                ret = model.formatted_attach_names
            return ret

        def on_model_change(self, form_, obj, is_created):

            session = MODELS_GLOBAL_CONTEXT['session']

            if is_created:
                if not (hasattr(form_, 'created_by') and form_.created_by and form_.created_by.data):
                    obj.created_by = flask_login.current_user.name
                if not (hasattr(form_, 'assignee') and form_.assignee and form_.assignee.data):
                    obj.assignee = session.query(User).filter(User.name == 'anonymous').first()

            if obj == obj.parent:
                obj.parent = None
                msg = 'Cannot make task {} parent of itself.'.format(obj.name)
                raise validators.ValidationError(msg)

            if hasattr(form_, 'status') and form_.status:
                next_ = form_.status.data

                if next_ in ('open', 'in_progress'):
                    if not obj.assignee or obj.assignee.name == 'anonymous':
                        msg = 'task {} must have a known assignee, to be {}.'.format(obj.name, next_)
                        raise validators.ValidationError(msg)

            if not is_created:
                _handle_task_modification(form_, obj.object_to_dict())

            ret = super(TaskView, self).on_model_change(form, obj, is_created)

            return ret

    class HistoryView(TrackerModelView):     # pylint: disable=unused-variable

        can_create = False
        can_delete = False
        can_edit = False

        column_labels = dict(user='Author', description="modifications", date_created="Date")

        column_searchable_list = (
            'task.id',
            'task.name',
            'user.name',
            'description',
        )

        column_filters = (
            # ~ 'description',
            'date_created',
            'task.name',
            'user.name',
        )

        column_list = (
            # ~ 'name',
            'task',
            'user',
            'date_created',
            'description',
        )

        def display_task(self, context, obj, name):   # pylint: disable=unused-argument,no-self-use

            t = getattr(obj, name)
            ret = t
            try:
                html_ = '<a href="/task/details/?id={}">{}</a> {}'.format(t.id, t.id_short or 0, t.name)
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        def display_modifications(self, context, obj, name):   # pylint: disable=unused-argument,no-self-use

            value = getattr(obj, name)
            ret = value
            try:
                value = json.loads(value)
                LINE_FMTR = ''
                LINE_FMTR += '<tr><td class="col-md-1">{}</td><td class="col-md-8">{}</td></tr>'
                html_ = ""
                html_ += '<table class="table table-striped table-bordered">'
                html_ += "".join([LINE_FMTR.format(k, v) for (k, v) in value])
                html_ += "</table>"
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        column_formatters = {
            'task': display_task,
            'description': display_modifications,
        }

    class AttachmentView(TrackerModelView):     # pylint: disable=unused-variable

        form_args = {
            'attached': {
                'label': 'attached task',
            },
        }

        column_filters = (
            'name',
            'date_modified',
            'description',
            'attached.name'
        )

        def get_create_form(self):

            form_ = super().get_create_form()
            form_.document = fields.FileField(u'Document')

            del form_.name

            return form_

        def after_model_delete(self, obj):

            ATTACHMENT_PATH = current_app.config.get('ATTACHMENT_PATH')

            stored_filename = os.path.join(ATTACHMENT_PATH, obj.name)
            if os.path.exists(stored_filename):
                os.remove(stored_filename)

            return super().after_model_delete(obj)

        def on_model_change(self, form_, obj, is_created):

            ATTACHMENT_PATH = current_app.config.get('ATTACHMENT_PATH')

            if hasattr(form_, 'document') and form_.document:

                if form_.document.data:
                    filename = secure_filename(form_.document.data.filename)
                    stored_filename = os.path.join(ATTACHMENT_PATH, filename)
                    form_.document.data.save(stored_filename)
                    obj.name = filename

            ret = super().on_model_change(form_, obj, is_created)
            return ret

    return locals()
