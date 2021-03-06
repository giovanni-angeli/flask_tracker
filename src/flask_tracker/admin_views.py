# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=broad-except

import os
import sys
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
from flask import Markup   # pylint: disable=import-error
from wtforms import (form, fields, validators)  # pylint: disable=import-error
import flask_login  # pylint: disable=import-error
from flask_admin.contrib.sqla import ModelView  # pylint: disable=import-error
from flask_admin.form.widgets import DatePickerWidget  # pylint: disable=import-error

from flask_tracker.models import (User, History, MODELS_GLOBAL_CONTEXT)


def has_capabilities(app, user, table_name, operation='*'):

    role = user.role
    cap_map = app.config.get('ROLE_CAPABILITY_MAP', {})
    default_cap = cap_map.get(role, {}).get('default')
    cap = cap_map.get(role, {}).get(table_name, default_cap)
    return cap is not None and (operation in cap or cap == '*')


def send_a_mail(email_client, msg_recipients, msg_subject, msg_body):

    from multiprocessing import Process

    def _do_send():
        t0 = time.time()
        for msg_recipient in msg_recipients:
            if msg_recipient:
                item = dict(dest=msg_recipient, msg_subject=msg_subject, msg_body=msg_body)
                email_client.send(**item)

        logging.warning("pid:{}, dt:{}".format(os.getpid(), time.time() - t0))
        sys.exit(0)

    p = Process(target=_do_send)
    p.start()
    # ~ p.join()


def get_current_user_name():
    logging.warning("flask_login.current_user.name:{}".format(flask_login.current_user.name))
    return flask_login.current_user.name


def _handle_item_modification(form_, item, current_app):     # pylint: disable=no-self-use, too-many-branches

    item_as_dict = item.object_to_dict()

    modifications = []
    deflt_ = form_.data.get('list_form_pk') is not None
    for k in form_.data.keys():
        try:
            if k == 'list_form_pk':
                continue
            if k == 'preview_content_button':
                continue
            if k == 'formatted_attach_names':
                continue

            a = form_.data[k]
            b = form_[k].object_data

            if not a and not b:
                continue

            if isinstance(a, list) and isinstance(b, list):
                a.sort(key=lambda x: x.name)
                b.sort(key=lambda x: x.name)

            if a != b:
                if k == 'content':
                    b = difflib.unified_diff(b.split('\n'), a.split('\n'), n=2,
                                             fromfile='before', tofile='after', fromfiledate=time.asctime())
                    b = Markup("<br/>".join(b))
                elif deflt_:
                    b = " --> {}".format(a)
                else:
                    b = "{} --> {}".format(b, a)
                modifications.append((k, str(b)))

        except Exception as exc:
            modifications.append((k, str(exc)))

    if modifications:

        session = MODELS_GLOBAL_CONTEXT['session']
        args = {
            '{}_id'.format(item.__tablename__): item_as_dict['id'],
            'user_id': flask_login.current_user.id,
            'description': json.dumps(modifications, indent=2)
        }
        logging.warning(json.dumps(args, indent=2))
        session.add(History(**args))

        msg_subject = "[FT Notify] - {}: {} modified".format(item.__tablename__, item.name)
        msg_body = json.dumps({
            item.__tablename__: item.name,
            'user': flask_login.current_user.name,
            'modifications': modifications
        }, indent=2)
        msg_recipients = [follower.email for follower in item.followers]

        email_client = getattr(current_app, 'email_client_tracker')
        if email_client:
            t0 = time.time()
            send_a_mail(email_client, msg_recipients, msg_subject, msg_body)
            logging.warning("pid:{}, dt:{}".format(os.getpid(), time.time() - t0))


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
    we define our ModelView classes inside a function, because
    we want an already initialized app to allow access to app.config.
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
            # 'name',
            'description',
        )

        def display_time_to_local_tz(self, context, obj, name):   # pylint: disable=unused-argument,no-self-use
            value = getattr(obj, name)
            value_ = value.replace(tzinfo=timezone.utc).astimezone().strftime("%d %b %Y (%I:%M:%S %p)")
            # ~ logging.warning("obj:{}, name:{}, value:{}, value_:{}".format(obj, name, value, value_))
            return Markup(value_)

        column_formatters = {
            'date_created': display_time_to_local_tz,
            'date_modified': display_time_to_local_tz,
        }

        def is_accessible(self):

            ret = False
            if flask_login.current_user.is_authenticated:

                self.can_edit = has_capabilities(           # pylint: disable=attribute-defined-outside-init
                    current_app, flask_login.current_user,
                    self.model.__tablename__, operation='e')
                self.can_create = has_capabilities(         # pylint: disable=attribute-defined-outside-init
                    current_app, flask_login.current_user,
                    self.model.__tablename__, operation='c')
                self.can_delete = has_capabilities(         # pylint: disable=attribute-defined-outside-init
                    current_app, flask_login.current_user,
                    self.model.__tablename__, operation='d')

                if has_capabilities(current_app, flask_login.current_user, self.model.__tablename__, operation='r'):
                    ret = True
            return ret

        def on_model_change(self, form_, obj, is_created):

            if is_created:
                if not has_capabilities(current_app, flask_login.current_user, self.model.__tablename__, operation='c'):
                    raise validators.ValidationError('permission denied on create')
            else:
                if not has_capabilities(current_app, flask_login.current_user, self.model.__tablename__, operation='e'):
                    raise validators.ValidationError('permission denied on edit')

            obj.date_modified = datetime.utcnow()
            ret = super(TrackerModelView, self).on_model_change(form_, obj, is_created)
            return ret

    class WorkTimeView(TrackerModelView):  # pylint: disable=unused-variable

        column_editable_list = (
            'duration',
            # ~ 'user',
            # ~ 'task',
            'date_created',
            'description',
        )

        column_sortable_list = (
            'date_created',
            ('user', ('user.name', )),
            ('task', ('task.name', )))

        column_list = (
            'date_created',
            'description',
            'duration',
            'user',
            'task',
        )

        column_details_exclude_list = (
            'date_modified',
        )

        column_labels = dict(date_created='Date')

        column_filters = (
            'date_created',
            'description',
            'user.name',
            'task.name',
            'task.milestone',
            'task',
        )

        form_args = {
            'user': {
                'default': get_current_user_name,
            },
        }

        def display_task(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use
            value = getattr(obj, name)
            ret = value
            try:
                html_ = '<a href="/task/details/?id={}" title="view task">{}</a>'.format(
                    obj.task_id, value)
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        column_formatters = TrackerModelView.column_formatters.copy()
        column_formatters.update({
            'task': display_task,
        })

        def get_create_form(self):

            form_ = super().get_create_form()

            def _local_now():
                date_utc_ = datetime.utcnow()
                date_local_ = date_utc_ - timedelta(seconds=time.timezone)
                logging.warning("date_local_:{}, date_utc_:{}".format(date_local_, date_utc_))
                return date_local_

            form_.date_created = fields.DateTimeField('date',
                                                      [validators.optional(),
                                                       validators.DataRequired()],
                                                      description='date of the activity',
                                                      default=_local_now)
            # ~ logging.warning("dir(form_.date_created):{}".format(dir(form_.date_created)))
            # ~ logging.warning("form_.date_created:{}".format(form_.date_created))

            return form_

        def on_model_change(self, form_, obj, is_created):

            if hasattr(form_, 'date_created') and form_.date_created:
                date_local_ = form_.date_created.data
                date_utc_ = date_local_ + timedelta(seconds=time.timezone)
                logging.warning("date_local_:{}, date_utc_:{}".format(date_local_, date_utc_))
                obj.date_created = date_utc_

            ret = super(WorkTimeView, self).on_model_change(form, obj, is_created)
            return ret

    class OrderView(TrackerModelView):    # pylint: disable=unused-variable

        column_editable_list = (
            'customer',
        )

        column_labels = dict(name='Code')

        column_list = (
            'customer',
            'name',
            'description',
            'amount',
            'date_created',
            'tasks',
        )

        column_formatters = TrackerModelView.column_formatters.copy()
        column_formatters.update({
            'tasks': _display_tasks_as_links,
        })

    class MilestoneView(TrackerModelView):   # pylint: disable=unused-variable

        column_editable_list = (
            # ~ 'project',
            'name',
            'project',
            'start_date',
            'due_date',
        )

        column_searchable_list = (
            'name',
            'description',
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

        column_formatters = TrackerModelView.column_formatters.copy()
        column_formatters.update({
            'tasks': _display_tasks_as_links,
        })

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

        # ~ can_create = False
        # ~ can_delete = False

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
            'role': [(k, k) for k in current_app.config.get('ROLE_CAPABILITY_MAP', {})],
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

    class ItemViewBase(TrackerModelView):     # pylint: disable=unused-variable

        def get_edit_form(self):

            form_ = super().get_edit_form()

            # ~ NOTE: The value of this filed will be updated in javascript on the edit page (i.e. at 'edit' time)
            form_.formatted_attach_names = fields.StringField(
                'attachments', render_kw=dict(value="*", readonly=True, height="1px"))

            cnt_description = Markup(
                'NOTE: you can use <a target="blank_" href="https://daringfireball.net/projects/markdown/syntax">Markdown syntax</a>. Use preview button to see what you get.')

            form_.content = fields.TextAreaField('content', [validators.optional(), validators.length(max=5 * 1000)],
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
                if hasattr(obj, 'assignee') and not (hasattr(form_, 'assignee')
                                                     and form_.assignee and form_.assignee.data):
                    obj.assignee = session.query(User).filter(User.name == 'anonymous').first()
                if hasattr(obj, 'owner') and not (hasattr(form_, 'owner') and form_.owner and form_.owner.data):
                    obj.owner = session.query(User).filter(User.name == 'anonymous').first()

            if hasattr(obj, 'parent') and obj == obj.parent:
                obj.parent = None
                msg = 'Cannot make task {} parent of itself.'.format(obj.name)
                raise validators.ValidationError(msg)

            if hasattr(form_, 'status') and form_.status:
                next_ = form_.status.data

                if next_ in ('open', 'in_progress'):
                    if hasattr(obj, 'assignee') and (not obj.assignee or obj.assignee.name == 'anonymous'):
                        msg = 'task {} must have a known assignee, to be {}.'.format(obj.name, next_)
                        raise validators.ValidationError(msg)

            if not is_created:
                _handle_item_modification(form_, obj, current_app)

            ret = super().on_model_change(form, obj, is_created)

            return ret

        def display_id_short(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use
            # ~ logging.warning("obj({}):{}".format(type(obj), obj))
            # ~ logging.warning("dir(obj):{}".format(dir(obj)))
            value = getattr(obj, name)
            ret = value
            try:
                html_ = '<a href="/history/?flt0_{0}_{0}_name_equals={1}" title="view history">{2}</a>'.format(
                    obj.__tablename__, urllib.parse.quote_plus(obj.name), value)
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        column_formatters = TrackerModelView.column_formatters.copy()
        column_formatters.update({
            'id_short': display_id_short,
        })

    class ClaimView(ItemViewBase):     # pylint: disable=unused-variable

        # ~ can_delete = current_app.config.get('CAN_DELETE_CLAIM', True)

        column_filters = (
            'name',
            'status',
            'date_created',
            'description',
            'owner.name',
            'followers.name',
            'customer.name',
            'machine_model',
            'serial_number',
            'installation_date',
            'installation_place',
            'date_created',
            'date_modified',
        )

        form_args = {
            'contact': {
                'label': 'Contact (email)',
            },
        }

        form_choices = {
            'damaged_group': current_app.config.get('CLAIM_GROUPS'),
            'machine_model': current_app.config.get('CLAIM_MACHINE_MODELS'),
            'status': current_app.config.get('ITEM_STATUSES'),
            'priority': current_app.config.get('ITEM_PRIORITIES'),
        }

        column_searchable_list = (
            'id',
            'name',
            'description',
            'machine_model',
            'serial_number',
        )

        form_columns = (
            'name',
            'description',
            'owner',
            'status',
            'priority',
            'customer',
            'followers',
            # ~ 'attachments',
            # ~ 'content',
            'contact',
            'machine_model',
            'serial_number',
            'installation_date',
            'installation_place',
            'quantity',
            'damaged_group',
            'serial_number_of_damaged_part',
            'customer',
            'owner',
            'the_part_have_been_requested',
            'is_covered_by_warranty',
            # ~ 'modifications',
            'followers',
        )

        column_list = (
            'name',
            'id_short',
            'description',
            'owner',
            'status',
            'customer',
            'priority',
            'date_created',
            'date_modified',
            # ~ 'followers',
            'machine_model',
            'serial_number',
            'installation_date',
            # ~ 'attachments',
        )

        column_details_list = (
            'id_short',
            'name',
            'description',
            'owner',
            'status',
            'priority',
            'customer',
            'attachments',
            'content',
            'contact',
            'machine_model',
            'serial_number',
            'installation_date',
            'installation_place',
            'quantity',
            'damaged_group',
            'serial_number_of_damaged_part',
            'the_part_have_been_requested',
            'is_covered_by_warranty',
            # ~ 'modifications',
            'followers',
        )

    class TaskView(ItemViewBase):     # pylint: disable=unused-variable

        column_sortable_list = (
            'name',
            'status',
            'category',
            'department',
            'date_created',
            'priority',
            ('assignee',
             ('assignee.name')),
            ('milestone',
             ('milestone.project.name',
              'milestone.name',
              'milestone.due_date')))

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
            'status': current_app.config.get('ITEM_STATUSES'),
            'priority': current_app.config.get('ITEM_PRIORITIES'),
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
            # 'order',
            'priority',
            # 'parent',
            'date_created',
            # 'followers',
            'worktimes',
            # ~ 'attachments',
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
            # ~ 'attachments',
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
            'followers.name',
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

        custom_row_actions = [
            ("/add_a_working_time_slot", '', 'fa fa-time glyphicon glyphicon-time',
             '_self', 'confirm adding hours?', 'Add Worked Hours'),
        ]

        def display_worktimes(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use
            total = sum([h.duration for h in obj.worktimes])
            ret = total
            try:
                html_ = '<a href="/worktime/?flt2_task_task_name_equals={}" title="view worked hrs details.">{}</a>'.format(
                    urllib.parse.quote_plus(obj.name), total)
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        def display_milestone(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use
            value = getattr(obj, name)
            ret = value
            try:
                html_ = '<a href="/milestone/details/?id={}" title="view milestone">{}</a>'.format(
                    obj.milestone_id, value)
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        column_formatters = ItemViewBase.column_formatters.copy()
        column_formatters.update({
            'milestone': display_milestone,
            'worktimes': display_worktimes,
        })

    class HistoryView(TrackerModelView):     # pylint: disable=unused-variable

        # ~ can_create = False
        # ~ can_delete = False
        # ~ can_edit = False

        column_labels = dict(user='Author', description="modifications", date_created="Date")

        column_sortable_list = (
            'date_created',
            ('claim', ('claim.name')),
            ('task', ('task.name')),
        )

        column_searchable_list = (
            'task.id',
            'task.name',
            'claim.id',
            'claim.name',
            'user.name',
            'description',
        )

        column_filters = (
            # ~ 'description',
            'date_created',
            'task.name',
            'claim.name',
            'user.name',
        )

        column_list = (
            # ~ 'name',
            'task',
            'claim',
            'user',
            'date_created',
            'description',
        )

        def display_item(self, context, obj, name):   # pylint: disable=unused-argument,no-self-use

            t = getattr(obj, name)
            ret = t
            if t is not None:
                try:
                    html_ = '<a href="/{}/details/?id={}">{}</a> {}'.format(name, t.id, t.id_short or 0, t.name)
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
                html_ += '<tr><td colspan="2" class="col-md-9"></td></tr>'
                html_ += "".join([LINE_FMTR.format(k, v) for (k, v) in value])
                html_ += "</table>"
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        column_formatters = TrackerModelView.column_formatters.copy()
        column_formatters.update({
            'task': display_item,
            'claim': display_item,
            'description': display_modifications,
        })

    class AttachmentView(TrackerModelView):     # pylint: disable=unused-variable

        form_args = {
            'attached': {
                'label': 'attached task',
            },
            'claimed': {
                'label': 'attached claim',
            },
            'description': {
                'label': 'title:TAGS',
            },
        }

        form_widget_args = {
            'name': {
                'readonly': True
            },
        }

        column_filters = (
            'name',
            'date_modified',
            'description',
            'attached.name'
        )

        column_searchable_list = (
            'name',
            'description',
        )

        def display_name(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use
            value = getattr(obj, name)
            ret = value
            try:
                html_ = '<a href="/attachment/{name}">{name}</a>'.format(name=obj.name)
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        column_formatters = TrackerModelView.column_formatters.copy()
        column_formatters.update({
            'name': display_name,
        })

        def get_edit_form(self):

            form_ = super().get_create_form()
            form_.document = fields.FileField(u'Document', default=self.display_name)
            return form_

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
