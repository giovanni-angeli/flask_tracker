# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=broad-except
# pylint: disable=logging-fstring-interpolation, consider-using-f-string, too-many-lines, logging-format-interpolation

import os
import sys
import logging
import traceback
import json
import time
import difflib
import re
import urllib.parse
from datetime import datetime, timezone, timedelta

from multiprocessing import Process

import ipaddress
import markdown  # pylint: disable=import-error

try:
    from werkzeug.utils import secure_filename  # pylint: disable=import-error, no-name-in-module
except Exception:
    from werkzeug import secure_filename  # pylint: disable=import-error, no-name-in-module

from jinja2 import contextfunction   # pylint: disable=import-error
from flask import (Markup, url_for)   # pylint: disable=import-error
from wtforms import (form, fields, validators)  # pylint: disable=import-error
import flask_login  # pylint: disable=import-error
from flask_admin.contrib.sqla import ModelView  # pylint: disable=import-error
from flask_admin.form.widgets import DatePickerWidget  # pylint: disable=import-error

from flask_tracker.models import (User, History, MODELS_GLOBAL_CONTEXT, ItemBase, Registry)

import unidecode # pylint: disable=import-error


def slugify(text):
    try:
        text = unidecode.unidecode(text).lower()
    except ModuleNotFoundError:
        text = text.lower()

    return re.sub(r'[\W_]+', '-', text)


def has_capabilities(app, user, table_name, operation='*'):

    role = user.role
    cap_map = app.config.get('ROLE_CAPABILITY_MAP', {})
    default_cap = cap_map.get(role, {}).get('default')
    cap = cap_map.get(role, {}).get(table_name, default_cap)
    return cap is not None and (operation in cap or cap == '*')


def send_a_mail(email_client, msg_recipients, msg_subject, msg_body):

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
                if k in ('content', 'lesson_learned'):
                    b_ = '' if b is None else b.split('\n')
                    a_ = '' if a is None else a.split('\n')
                    b = difflib.unified_diff(
                        b_, a_, n=2, fromfile='before', tofile='after', fromfiledate=time.asctime())
                    b = Markup("<br/>".join(b))
                elif deflt_:
                    b = " --> {}".format(a)
                else:
                    b = "{} --> {}".format(b, a)
                modifications.append((k, str(b)))

        except Exception as exc:
            modifications.append((k, str(exc)))

    if modifications:

        args = {
            '{}_id'.format(item.__tablename__): item_as_dict['id'],
            'user_id': flask_login.current_user.id,
            'description': json.dumps(modifications, indent=2)
        }
        logging.warning(json.dumps(args, indent=2))
        history_obj = None
        session = None

        if hasattr(History, '{}_id'.format(item.__tablename__)):

            session = MODELS_GLOBAL_CONTEXT['session']
            history_obj = History(**args)
            session.add(history_obj)

        if hasattr(item, 'followers') and item.followers:
            if session:
                session.flush()
            svr_ip = current_app.config.get("HOST")
            if current_app.config.get("IPV4_BY_HOSTNAME", False):
                # Translate a host name to IPv4 address format
                import socket   # pylint: disable=import-outside-toplevel
                hostname = socket.gethostname()
                svr_ip = socket.gethostbyname(hostname)

            msg_subject = "[FT Notify] - {}: {} modified".format(item.__tablename__, item.name)
            msg_body = json.dumps({
                item.__tablename__: item.name,
                'user': flask_login.current_user.name,
                'direct url':"http://{}:{}/history/details/?id={}&url=%2Fhistory%2F".format(
                    svr_ip,
                    current_app.config.get("PORT"),
                    history_obj.id)
            }, indent=2)
            msg_recipients = [follower.email for follower in item.followers]
            # logging.warning(f'msg_body > {msg_body}')
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


def _display_time_to_local_tz(cls, context, obj, name):   # pylint: disable=unused-argument
    value = getattr(obj, name)
    if value:
        value_ = value.replace(tzinfo=timezone.utc).astimezone().strftime("%d %b %Y (%I:%M:%S %p)")
    else:
        value_ = value
    return Markup(value_)


def _display_description(cls, context, obj, name):   # pylint: disable=unused-argument,no-self-use
    value = getattr(obj, name)
    return Markup(value)


def _colorize_diffs(diff):
    # adapted from https://github.com/kilink/ghdiff
    import six #pylint: disable=import-outside-toplevel

    def _colorize(diff):
        if isinstance(diff, six.string_types):
            lines = diff.splitlines()
        else:
            lines = diff
        lines.reverse()
        while lines and not lines[-1].startswith("@@"):
            lines.pop()
        yield '<div class="diff">'
        while lines:
            line = lines.pop()
            klass = ""
            if line.startswith("@@"):
                klass = "control"
            elif line.startswith("-"):
                klass = "delete"
            elif line.startswith("+"):
                klass = "insert"
            yield '<div class="%s">%s</div>' % (klass, line,)
        yield "</div>"

    default_css = """\
        <style type="text/css">
            .diff {
                border: 1px solid #cccccc;
                background: none repeat scroll 0 0 #f8f8f8;
                font-family: 'Bitstream Vera Sans Mono','Courier',monospace;
                font-size: 12px;
                line-height: 1.4;
                white-space: normal;
                word-wrap: break-word;
                width: 1025px !important;
            }
            .diff div:hover {
                background-color:#ffc;
            }
            .diff .control {
                background-color: #eaf2f5;
                color: #999999;
            }
            .diff .insert {
                background-color: #ddffdd;
                color: #000000;
            }
            .diff .delete {
                background-color: #ffdddd;
                color: #000000;
            }
        </style>
        """
    diff = diff.replace('<br/>', '\n')
    colorized_diff =  default_css + "\n".join(_colorize(diff))
    return colorized_diff


def _handle_json_schema(obj, deflt_schema=None):

    _schema = {}
    _value = None
    _error = None
    model_name = obj.__class__.__name__.lower()

    if deflt_schema:
        _value = {p:deflt_schema['properties'][p]['default'] for p in deflt_schema['properties']}
        deflt_schema['title'] = "New Registry Machine"
        _schema = deflt_schema

    if obj is not None and model_name == 'registry':
        try:
            title = "{} machine sn: {}".format(model_name, obj.sn)
            if obj and obj.json_info:
                _value = json.loads(obj.json_info)
                _schema['title'] = title

        except Exception as exc:
            logging.warning("exc: {}".format(exc))

    _schema = Markup(_schema)
    _value = Markup(_value)

    return _schema, _value, _error


def define_view_classes(current_app):  # pylint: disable=too-many-statements
    """
    we define our ModelView classes inside a function, because
    we want an already initialized app to allow access to app.config.
    """

    class TrackerModelView(ModelView):    # pylint: disable=unused-variable, possibly-unused-variable

        named_filter_urls = True

        can_view_details = True
        can_export = True
        export_max_rows = 1000
        export_types = ['csv', 'json']

        details_template = "admin/details.html"
        list_template = 'admin/list.html'
        create_template = 'admin/create.html'
        edit_template = 'admin/edit.html'

        column_default_sort = ('date_created', True)

        column_searchable_list = (
            # 'name',
            'description',
        )

        column_formatters = {
            'date_created': _display_time_to_local_tz,
            'date_modified': _display_time_to_local_tz,
            'description': _display_description,
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

        def on_model_change(self, form_, obj, is_created): # pylint: disable=super-with-arguments

            if is_created:
                if not has_capabilities(current_app, flask_login.current_user, self.model.__tablename__, operation='c'):
                    raise validators.ValidationError('permission denied on create')
            else:
                if not has_capabilities(current_app, flask_login.current_user, self.model.__tablename__, operation='e'):
                    raise validators.ValidationError('permission denied on edit')

            obj.date_modified = datetime.utcnow()
            ret = super(TrackerModelView, self).on_model_change(form_, obj, is_created) # pylint: disable=super-with-arguments
            return ret

    class WorkTimeBaseView(TrackerModelView):  # pylint: disable=unused-variable, possibly-unused-variable

        column_editable_list = [
            'duration',
            'date_created',
            'description',
        ]

        column_sortable_list = [
            'date_created',
            ('user', ('user.name', ))
        ]

        column_list = [
            'date_created',
            'description',
            'duration',
            'user',
        ]

        column_details_exclude_list = [
            'date_modified',
        ]

        column_labels = dict(date_created='Date')

        column_filters = [
            'date_created',
            'description',
            'user.name',
        ]

        form_args = {
            'user': {
                'default': get_current_user_name,
            },
        }

        def get_create_form(self):

            form_ = super().get_create_form()

            def _local_now():
                date_utc_ = datetime.utcnow()
                date_local_ = date_utc_ - timedelta(seconds=time.timezone)
                logging.warning("date_local_:{}, date_utc_:{}".format(date_local_, date_utc_))
                return date_local_

            form_.date_created = fields.DateTimeField(
                'date',
                [validators.optional(),
                 validators.DataRequired()],
                description='date of the activity',
                default=_local_now
            )

            return form_

        def on_model_change(self, form_, obj, is_created):

            if hasattr(form_, 'date_created') and form_.date_created:
                date_local_ = form_.date_created.data
                date_utc_ = date_local_ + timedelta(seconds=time.timezone)
                logging.warning("date_local_:{}, date_utc_:{}".format(date_local_, date_utc_))
                obj.date_created = date_utc_

            ret = super().on_model_change(form, obj, is_created)
            return ret

    class WorkTimeView(WorkTimeBaseView):  # pylint: disable=unused-variable, possibly-unused-variable

        column_sortable_list = WorkTimeBaseView.column_sortable_list.copy()
        column_sortable_list += [('task', ('task.name', ))]

        column_list = WorkTimeBaseView.column_list.copy()
        column_list += ['task',]

        column_filters = WorkTimeBaseView.column_filters.copy()
        column_filters += [
            'task.name',
            'task.milestone',
            'task',
        ]

        column_export_list = WorkTimeBaseView.column_list.copy()
        column_export_list += ['task.name']

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

    class WorkTimeClaimView(TrackerModelView):  # pylint: disable=unused-variable, possibly-unused-variable

        column_sortable_list = WorkTimeBaseView.column_sortable_list.copy()
        column_sortable_list += [('claim', ('claim.name', ))]

        column_list = WorkTimeBaseView.column_list.copy()
        column_list += ['claim',]

        column_filters = WorkTimeBaseView.column_filters.copy()
        column_filters += ['claim', ]

        column_export_list = WorkTimeBaseView.column_list.copy()
        column_export_list += ['claim.name']

        def display_claim(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use
            value = getattr(obj, name)
            ret = value
            try:
                html_ = '<a href="/claim/details/?id={}" title="view claim">{}</a>'.format(
                    obj.claim_id, value)
                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        column_formatters = TrackerModelView.column_formatters.copy()
        column_formatters.update({
            'claim': display_claim,
        })

    class OrderView(TrackerModelView):    # pylint: disable=unused-variable, possibly-unused-variable

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

    class MilestoneView(TrackerModelView):   # pylint: disable=unused-variable, possibly-unused-variable

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

    class ProjectView(TrackerModelView):      # pylint: disable=unused-variable, possibly-unused-variable

        column_editable_list = (
            # ~ 'milestones',
            # ~ 'orders',
        )

        column_list = (
            'name',
            'description',
        )

    class UserView(TrackerModelView):     # pylint: disable=unused-variable, possibly-unused-variable

        # ~ can_create = False
        # ~ can_delete = False

        column_searchable_list = (
            'name',
            'role',
            'email',
        )

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
            'assigned_improvements',
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

        column_labels = dict(
            worktimes='Worked Hours in This Week',
            followed='Followed Tasks'
        )

    class ItemViewBase(TrackerModelView):     # pylint: disable=unused-variable, possibly-unused-variable

        def get_edit_form(self):

            form_ = super().get_edit_form()

            # ~ NOTE: The value of this filed will be updated in javascript on the edit page (i.e. at 'edit' time)
            form_.formatted_attach_names = fields.StringField(
                'attachments', render_kw=dict(value="*", readonly=True, height="1px"))

            cnt_description = Markup(
                'NOTE: you can use <a target="blank_" href="https://daringfireball.net/projects/markdown/syntax">Markdown syntax</a>. Use preview button to see what you get.')

            form_.content = fields.TextAreaField(
                'content',
                [validators.optional(), validators.length(max=ItemBase.content_max_len)],
                description=cnt_description,
                render_kw={
                    "style": "background:#fff; border:dashed #DD3333 1px; height:480px;"},
            )

            form_.preview_content_button = fields.BooleanField(u'preview content', [], render_kw={})

            if isinstance(self, (ClaimView, TaskView)):
                form_.lesson_learned = fields.TextAreaField(
                    'lesson_learned',
                    [validators.optional(), validators.length(max=ItemBase.content_max_len)],
                    render_kw={
                        "style": "background:#fff; border:dashed #DD3333 1px; height:300px;"},
                )

            return form_

        @contextfunction
        def get_detail_value(self, context, model, name):

            ret = super().get_detail_value(context, model, name)
            if name == 'content':
                ret = markdown.markdown(ret)
                ret = Markup(ret)
            elif name == 'attachments':
                ret = model.formatted_attach_names

                html_ret = ""
                for a in ret:
                    html_ = '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a></br>'.format(
                        url_for('attachment', filename=a), a)
                    html_ret += Markup(html_)
                ret = html_ret

            return ret

        def on_model_change(self, form_, obj, is_created):

            session = MODELS_GLOBAL_CONTEXT['session']

            map_model_attribute = {
                'improvement': 'assignee',
                'task': 'assignee',
                'claim': 'owner',
            }

            if is_created:
                if not (hasattr(form_, 'created_by') and form_.created_by and form_.created_by.data):
                    obj.created_by = flask_login.current_user.name

                obj_attr = map_model_attribute.get(obj.__tablename__)
                if hasattr(obj, obj_attr):
                    form_attr = getattr(form_, obj_attr, None)
                    if hasattr(form_, obj_attr) and form_attr and getattr(form_attr, 'data', None):
                        usrname = getattr(form_attr, 'data', 'anonymous')
                        usr = session.query(User).filter(User.name == str(usrname)).first()
                        setattr(obj, obj_attr, usr)
                    else:
                        anon_usr = session.query(User).filter(User.name == 'anonymous').first()
                        setattr(obj, obj_attr, anon_usr)

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

            # if not is_created:
            _handle_item_modification(form_, obj, current_app)

            ret = super().on_model_change(form_, obj, is_created)

            return ret

        def display_content(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use
            value = getattr(obj, name)
            value = markdown.markdown(value)
            value = Markup(value)
            return value

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
            'content': display_content,
        })

        column_export_list = [
            'name',
            'id',
            'description',
            'priority',
            'status',
            'date_created',
            'date_modified',
        ]

        column_formatters_export = dict(
           id=lambda v, c, m, p: m.id[:4].upper(),
       )

    class ClaimView(ItemViewBase):     # pylint: disable=unused-variable, possibly-unused-variable

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
            'damaged_group',
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
            'department': current_app.config.get('DEPARTMENTS'),
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
            'department',
            'milestone',
            'customer',
            'owner',
            'teamleader',
            'followers',
            'resources',
            'start_date',
            'due_date',
            'completion',
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
            'the_part_have_been_requested',
            'is_covered_by_warranty',
            # ~ 'modifications',
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
            'damaged_group',
            'worktimes_claim',
        )

        column_details_list = (
            'id_short',
            'name',
            'description',
            'owner',
            'status',
            'priority',
            'department',
            'milestone',
            'customer',
            'owner',
            'teamleader',
            'followers',
            'resources',
            'start_date',
            'due_date',
            'completion',
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
            'worktimes_claim',
            'lesson_learned',
        )

        column_export_list = ItemViewBase.column_export_list.copy()
        column_export_list += [
            'customer',
            'machine_model',
            'serial_number',
            'installation_date',
            'damaged_group',
            'owner',
            'teamleader.name',
            'followers',
            'resources',
            'planned_time',
            'start_date',
            'due_date',
            'worktimes_claim',
            'completion',
            'lesson_learned',
        ]

        column_formatters_export = ItemViewBase.column_formatters_export.copy()
        column_formatters_export.update(
            dict(worktimes_claim=lambda v, c, m, p: '0' if m.worktimes_claim is None else sum([h.duration for h in m.worktimes_claim]),
            )
        )

        custom_row_actions = [
            ("/add_a_working_claim_time_slot", '', 'fa fa-time glyphicon glyphicon-time',
             '_self', 'confirm adding hours?', 'Add Worked Hours'),
        ]

        def display_worktimes_claim(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use

            total = sum([h.duration for h in obj.worktimes_claim])
            ret = total
            try:
                html_ = '<a href="/worktimeclaim/?flt2_claim_name_equals={}" title="view worked hrs details.">{}</a>'.format(
                    urllib.parse.quote_plus(obj.name), total)

                ret = Markup(html_)
            except BaseException:
                logging.warning(traceback.format_exc())
            return ret

        column_formatters = ItemViewBase.column_formatters.copy()
        column_formatters.update({
            'worktimes_claim': display_worktimes_claim,
        })

        column_labels = dict(completion='Completion %')

    class TaskView(ItemViewBase):     # pylint: disable=unused-variable, possibly-unused-variable

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
            'attachments',
            'teamleader',
            'resources',
            'planned_time',
            'start_date',
            'due_date',
            'completion',
            'lesson_learned',
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
            'teamleader',
            'followers',
            'resources',
            # ~ 'attachments',
            # ~ 'content',
            'planned_time',
            'start_date',
            'due_date',
            'completion',
        )

        column_export_list = ItemViewBase.column_export_list.copy()
        column_export_list += [
            'category',
            'department',
            'milestone.name',
            'worktimes',
            'order',
            'assignee',
            'teamleader.name',
            'followers',
            'resources',
            'planned_time',
            'start_date',
            'due_date',
            'completion',
            'lesson_learned',
        ]

        column_formatters_export = ItemViewBase.column_formatters_export.copy()
        column_formatters_export.update(
            dict(worktimes=lambda v, c, m, p: '0' if m.worktimes is None else sum([h.duration for h in m.worktimes]),
            )
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

        column_labels = dict(completion='Completion %')

    class ImprovementView(ItemViewBase):     # pylint: disable=unused-variable, possibly-unused-variable
        improvement_depts = (
            'R&D',
            'PRODUZIONE',
            'SERVICE',
            'COMMERCIALE',
            'MARKETING',
            'QUALITÀ'
        )

        form_choices = {
            'machine_model': current_app.config.get('CLAIM_MACHINE_MODELS'),
            'status': current_app.config.get('ITEM_STATUSES'),
            'priority': current_app.config.get('ITEM_PRIORITIES'),
            'market_potential': current_app.config.get('IMPROVEMENT_MARKET_POTENTIAL', [(slugify(l), l.capitalize()) for l in (
                'minimal',
                'low',
                'medium',
                'high',
                'maximal')]),
            'category': current_app.config.get('IMPROVEMENT_CATEGORIES', [(slugify(l), l.capitalize()) for l in (
                'Funzionalità',
                'Affidabilità',
                'Economia',
                'Assemblaggio',
                'Manutenzione',
                'Qualità',
                'Ergonomia',
                'Sicurezza',
                'Trasporto',
                'Diagnostica',
                'Estetica',
                'Modularità',
                'Collaudo')]),
            'assembly_subgroup': current_app.config.get('IMPROVEMENT_ASSEMBLY_SUBGROUPS', [(slugify(l), l.capitalize()) for l in (
                'valvola 3 vie 2 posizioni DN4/6',
                'pompa 0.2LT',
                'pompa 0.5LT',
                'pompa 1.5LT',
                'pompa 3LT',
                'valvola ceramica Thor')]),
            'department': current_app.config.get('IMPROVEMENT_DEPARTMENTS', [(l, l.capitalize()) for l in improvement_depts]),
            'target_department': current_app.config.get('IMPROVEMENT_DEPARTMENTS', [(l, l.capitalize()) for l in improvement_depts])
        }

        column_filters = (
            'name',
            'description',
            'status',
            'priority',
            'department',
            'target_department',
            'machine_model',
            'due_date',
            'category',
            'assembly_subgroup',
            'component',
            'market_potential',
            'customer.name',
            'assignee.name',
            'author.name',
        )

        form_columns = (
            'name',
            'description',
            'status',
            'priority',
            'department',
            'target_department',
            'followers',
            'machine_model',
            'due_date',
            'category',
            'assembly_subgroup',
            'component',
            'market_potential',
            'estimated_resources',
            'estimated_time_steps',
            # ~ 'created_by',
            'notes',
            'customer',
            'author',
            'assignee',
            # 'notifier',
            'content',
        )

        column_list = (
            'name',
            'id_short',
            'description',
            'status',
            'priority',
            'department',
            'target_department',
            'machine_model',
            'due_date',
            'category',
            'assembly_subgroup',
            'component',
            'market_potential',
            'estimated_resources',
            'estimated_time_steps',
            # ~ 'created_by',
            'notes',
            'customer',
            'author',
            'assignee',
            # 'notifier',
        )

        column_details_list = (
            'date_created',
            'date_modified',
            'name',
            'id_short',
            'description',
            'status',
            'priority',
            'department',
            'target_department',
            'followers',
            'machine_model',
            'due_date',
            'category',
            'assembly_subgroup',
            'component',
            'market_potential',
            'content',
            'estimated_resources',
            'estimated_time_steps',
            'notes',
            'customer',
            'assignee',
            # 'notifier',
        )

        # ~ form_excluded_columns = (
        # ~ 'date_created',
        # ~ 'date_modified',
        # ~ )

        column_editable_list = (
            'status',
            'category',
            'customer',
            'author',
            'assignee',
            # 'notifier',
            'due_date',
            'followers',
        )

        column_formatters = ItemViewBase.column_formatters.copy()
        column_formatters.update({
            'due_date': _display_time_to_local_tz,
        })

        def get_create_form(self):

            form_ = super().get_create_form()

            form_.content = fields.TextAreaField(
                'content',
                [validators.optional(), validators.length(max=ItemBase.content_max_len)],
                default="",
                render_kw={
                    "style": "background:#fff; border:dashed #DD3333 1px; height:480px;"},
            )

            return form_

    class HistoryView(TrackerModelView):     # pylint: disable=unused-variable, possibly-unused-variable

        # ~ can_create = False
        # ~ can_delete = False
        # ~ can_edit = False

        column_labels = dict(user='Author', description="modifications", date_created="Date")

        column_sortable_list = (
            'date_created',
            ('claim', ('claim.name')),
            ('task', ('task.name')),
            ('improvement', ('improvement.name')),
        )

        column_searchable_list = (
            'task.id',
            'task.name',
            'claim.id',
            'claim.name',
            'improvement.id',
            'improvement.name',
            'user.name',
            'description',
        )

        column_filters = (
            # ~ 'description',
            'date_created',
            'task.name',
            'claim.name',
            'improvement.name',
            'user.name',
        )

        column_list = (
            # ~ 'name',
            'task',
            'claim',
            'improvement',
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
                for i, v in enumerate(value):
                    if v[0] in ('content', 'lesson_learned'):
                        value[i][1] = _colorize_diffs(v[1])

                LINE_FMTR = ''
                LINE_FMTR += '<tr><td class="col-md-1">{}</td><td class="col-md-8">{}</td></tr>'
                html_ = ""
                html_ += '<table class="table table-striped table-bordered" style="width: 1025px !important;>'
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
            'improvement': display_item,
            'description': display_modifications,
        })

    class AttachmentView(TrackerModelView):     # pylint: disable=unused-variable, possibly-unused-variable

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

    class RegistryView(TrackerModelView):   # pylint: disable=unused-variable, possibly-unused-variable

        column_list = (
            'created_by',
            'modified_by',
            'date_created',
            'date_modified',
            'sn',
            'machine_model',
            'customer',
            'description',
            'vpn',
            'notes',
        )

        column_searchable_list = (
            'sn',
            'vpn',
            'machine_model',
            'json_info',
        )

        column_details_list = (
            'date_created',
            'date_modified',
            'created_by',
            'modified_by',
            'sn',
            'machine_model',
            'customer',
            'description',
            'vpn',
            'notes',
            'json_info',
        )

        form_columns = [
            'sn',
            'machine_model',
            'customer',
            'description',
            'vpn',
            'notes',
            'json_info'
        ]

        column_labels = dict(sn='Serial Number')

        form_choices = {
            'machine_model': current_app.config.get('REGISTRY_MODELS'),
        }

        column_filters = (
            'customer.name',
            'machine_model',
            'description',
            'json_info',
        )

        def edit_form(self, *args, **kwargs):

            obj = kwargs.get('obj')
            deflt_jsonschema = current_app.config.get('JSONSCHEMA_REGISTRY', {})
            schema, value, error = _handle_json_schema(
                obj=obj, deflt_schema=deflt_jsonschema)

            form_ = super().edit_form(*args, **kwargs)

            form_.extra_args = {
                'jsonschema': schema,
                'jsonvalue': value,
                'error': error, }

            # logging.warning("form.extra_args:{}".format(form.extra_args))

            return form_

        def create_form(self, *args, **kwargs):

            obj = kwargs.get('obj')
            deflt_jsonschema = current_app.config.get('JSONSCHEMA_REGISTRY', {})
            schema, value, error = _handle_json_schema(
                obj=obj, deflt_schema=deflt_jsonschema)

            form_ = super().create_form(*args, **kwargs)

            form_.extra_args = {
                'jsonschema': schema,
                'jsonvalue': value,
                'error': error, }

            # logging.warning("form.extra_args:{}".format(form.extra_args))

            return form_

        def get_create_form(self):

            form_ = super().get_create_form()

            form_.notes = fields.TextAreaField(
                'notes',
                [validators.optional(), validators.length(max=Registry.content_max_len)],
                render_kw={
                    "style": "background:#fff; border:dashed #DD3333 1px; height:240px;"
                },
            )

            return form_

        def get_edit_form(self):

            form_ = super().get_edit_form()

            form_.notes = fields.TextAreaField(
                'notes',
                [validators.optional(), validators.length(max=Registry.content_max_len)],
                render_kw={
                    "style": "background:#fff; border:dashed #DD3333 1px; height:240px;"
                },
            )

            return form_

        def display_notes(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use
            value = getattr(obj, name)
            # logging.warning(f'value: {value}')
            value = markdown.markdown(value)
            value = Markup(value)
            return value

        def display_json_info(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use

            def _dict_to_html_table(_dict, _selected_field_names=None):

                if _selected_field_names is None:
                    _selected_field_names = list(_dict.keys())

                _html_table = '<table class="table table-striped table-bordered"><tr>'
                _html_table += '</tr><tr>'.join([f'<td>{k}:</td> <td class="{k}"><code>{_dict[k]}</code></td>'
                                                 for k in _selected_field_names if _dict.get(k, '--undefined--') != '--undefined--'])
                _html_table += '</tr></table>'

                return _html_table

            value = getattr(obj, name) #it is a string
            value_ = json.loads(value)
            logging.debug(f'value({type(value_)})')
            for k in value_:
                v_ = value_.get(k)
                if k == 'alfa40_platform_info':
                    value_[k] = v_.replace('\n', '<br>')
                if k == 'cmd_info':
                    value_[k] = v_.replace(',', ',\n<br>')

            json_info_html_table = _dict_to_html_table(value_)
            value = markdown.markdown(json_info_html_table)
            value = Markup(value)
            return value

        column_formatters = TrackerModelView.column_formatters.copy()
        column_formatters.update({
            'notes': display_notes,
            'json_info': display_json_info,
        })

        column_formatters_detail = {
            'json_info': display_json_info,
        }

        def on_model_change(self, form_, obj, is_created):

            dict_json_info = None

            try:
                dict_json_info = json.loads(obj.json_info)
                err_msg_no_plat_info = 'Missing ALFA40 PLATFORM values'
                err_msg_no_cmd_info = 'Missing CMD INFO values'
                assert dict_json_info.get('alfa40_platform_info'), err_msg_no_plat_info
                assert dict_json_info.get('cmd_info'), err_msg_no_cmd_info

                if obj.sn:
                    form_sn = obj.sn
                    err_msg_sn = f'Machine Serial Number MUST contains only numbers!! FOUND "{obj.sn}".'
                    assert form_sn.isdigit(), err_msg_sn

                    alfa40_platfrm_sn = json.loads(dict_json_info.get('alfa40_platform_info', {})).get('alfa SN', '')[0]
                    err_msg_equal_sn = f'Machine Serial Number "{form_sn}" and ALFA40 PLATFORM SN "{alfa40_platfrm_sn}" NOT equals !'
                    assert form_sn == alfa40_platfrm_sn, err_msg_equal_sn

                if obj.vpn:
                    err_msg_vpn = f'Machine Serial Number "{obj.vpn}" MUST be a valid IPv4 address !'
                    assert ipaddress.ip_address(obj.vpn), err_msg_vpn

            except (AssertionError, ValueError) as e:
                form_.extra_args['jsonvalue'] = Markup(dict_json_info)
                logging.warning(f'ValidationError: {e}')
                raise validators.ValidationError(e)


            if is_created and not (hasattr(form_, 'created_by') and obj.created_by):
                obj.created_by = flask_login.current_user.name

            if not is_created and not hasattr(form_, 'modified_by'):
                obj.modified_by = flask_login.current_user.name

            ret = super().on_model_change(form_, obj, is_created)

            return ret

    return locals()
