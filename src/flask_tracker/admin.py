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
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from functools import wraps

import markdown  # pylint: disable=import-error
from werkzeug import secure_filename
from werkzeug.security import check_password_hash  # pylint: disable=import-error
from jinja2 import contextfunction   # pylint: disable=import-error
from flask import (flash, Markup, url_for, redirect, request, current_app, send_from_directory)  # pylint: disable=import-error
from wtforms import (form, fields, validators)  # pylint: disable=import-error
import flask_login  # pylint: disable=import-error
import flask_admin  # pylint: disable=import-error
from flask_admin.base import Admin, MenuLink    # pylint: disable=import-error
from flask_admin.contrib.sqla import ModelView  # pylint: disable=import-error
from flask_admin.form.widgets import DatePickerWidget  # pylint: disable=import-error

from flask_tracker.models import (
    Task,
    Project,
    Milestone,
    Customer,
    Order,
    User,
    WorkTime,
    Attachment,
    MODELS_GLOBAL_CONTEXT,
    get_package_version)


def get_start_of_week():

    today = datetime.now().date()
    start_of_the_week = today - timedelta(days=today.weekday())
    start_of_the_week = start_of_the_week.strftime("%Y-%m-%d+00:00:00")
    start_of_the_week = Markup(start_of_the_week)
    return start_of_the_week


def get_start_of_month():

    today = datetime.now().date()
    start_of_the_month = today - timedelta(days=today.day)
    start_of_the_month = start_of_the_month.strftime("%Y-%m-%d+23:59:00")
    start_of_the_month = Markup(start_of_the_month)
    return start_of_the_month


def compile_filtered_url(model_name, filters):

    # ~ "/task/?flt2_project_project_name_in_list=a%2Cg"
    url_ = "/{}/?".format(model_name)
    filter_as_strings = []
    for n, (f_name, opr, arg) in enumerate(filters):
        assert opr in (
            'equals', 'contains', 'in_list', 'not_equal', 'not_contains', 'not_in_list', 'empty',
            'greater_than', 'smaller_than', 'between', 'not_between',
        ), "unrecognized operator '{}' in compile_filtered_url()".format(opr)

        if isinstance(arg, (list, tuple, set)):
            arg = ",".join(arg)
        filter_as_strings.append("flt{}_{}_{}={}".format(n, f_name, opr, arg))
    url_ += '&'.join(filter_as_strings)
    url_ = quote(url_, safe='/?&=+')
    return url_


def protect(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not flask_login.current_user.is_authenticated:
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)

    return wrapper


class LoginForm(form.Form):

    login = fields.StringField(validators=[validators.DataRequired()])
    password = fields.PasswordField(validators=[validators.DataRequired()])

    def validate_login(self, field):

        logging.warning("self.login.data:{}".format(self.login.data))

        user = self.get_user()

        logging.warning("user:{}, field:{}".format(user, field))

        if user is None:
            raise validators.ValidationError('Invalid user')

        # we're comparing the plaintext pw with the the hash from the db
        if not check_password_hash(user.password, self.password.data):
            # to compare plain text passwords use
            # if user.password != self.password.data:
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        session = MODELS_GLOBAL_CONTEXT['session']
        return session.query(User).filter_by(name=self.login.data).first()


class TrackerAdminResources(flask_admin.AdminIndexView):

    @flask_admin.expose("/")
    @flask_admin.expose("/home")
    @flask_admin.expose("/index")
    @protect
    def index(self, ):

        t0 = time.time()

        session = MODELS_GLOBAL_CONTEXT['session']

        start_of_the_week = get_start_of_week()
        start_of_the_month = get_start_of_month()
        user_name = flask_login.current_user.name

        MAX_OPEN_TASK_PER_USER = current_app.config.get('MAX_OPEN_TASK_PER_USER', 20)
        TASK_CATHEGORIES = current_app.config.get('TASK_CATHEGORIES', [])
        DEPARTMENTS = current_app.config.get('DEPARTMENTS', [])

        assigned_task_names = ["{}::{}".format(t.name, t.description or "")[:64] for t in session.query(Task).filter(Task.status == 'in_progress').filter(
            Task.assignee_id == flask_login.current_user.id).limit(MAX_OPEN_TASK_PER_USER)]

        task_filtered_views = [
            ('all open tasks', compile_filtered_url('task', [('status', 'equals', 'open')])),
            ('all tasks in progress', compile_filtered_url('task', [('status', 'equals', 'in_progress')])),
            ('all tasks followed by <b>{}</b>'.format(user_name),
             compile_filtered_url('task', [('user_name', 'equals', user_name)])),
            ('tasks assigned to <b>{}</b> open or in progress'.format(user_name),
             compile_filtered_url('task', [('assignee_user_name', 'equals', user_name), ('status', 'in_list', ('open', 'in_progress'))])),
            ('all tasks assigned to <b>{}</b>'.format(user_name),
             compile_filtered_url('task', [('assignee_user_name', 'equals', user_name)])),
        ]

        worktime_filtered_views = [
            ('hours worked by <b>{}</b>, in this week'.format(user_name),
             compile_filtered_url('worktime', [('date', 'greater_than', start_of_the_week), ('user_user_name', 'equals', user_name)])),
            ('hours worked by <b>{}</b>, in this month'.format(user_name),
             compile_filtered_url('worktime', [('date', 'greater_than', start_of_the_month), ('user_user_name', 'equals', user_name)])),
        ]

        project_names = sorted([o.name for o in session.query(Project).limit(50)])
        order_names = sorted([o.name for o in session.query(Order).limit(50) if o.in_progress])
        milestone_names = sorted([o.name for o in session.query(Milestone).limit(50) if o.in_progress])
        user_names = sorted([o.name for o in session.query(User).limit(50)])
        cathegory_names = sorted([n[0] for n in TASK_CATHEGORIES])
        department_names = sorted([n[0] for n in DEPARTMENTS])

        ctx = {
            'projects': project_names,
            'orders': order_names,
            'milestones': milestone_names,
            'users': user_names,
            'cathegories': cathegory_names,
            'departments': department_names,
            'version': get_package_version(),
            'assigned_task_names': assigned_task_names,
            'task_filtered_views': [(Markup("{}. {}".format(i, view[0])), view[1]) for i, view in enumerate(task_filtered_views)],
            'worktime_filtered_views': [(Markup("{}. {}".format(i, view[0])), view[1]) for i, view in enumerate(worktime_filtered_views)],
        }

        logging.warning("dt:{}".format(time.time() - t0))

        return self.render(self._template, **ctx)

    @flask_admin.expose('/login/', methods=('GET', 'POST'))
    def login(self):

        form_ = LoginForm(request.form)

        logging.warning("form_:{}".format(form_))

        if flask_admin.helpers.validate_form_on_submit(form_):
            user = form_.get_user()
            flask_login.login_user(user)
            logging.warning("user.name:{}".format(user.name))

        logging.warning("login.current_user:{}".format(flask_login.current_user))

        if flask_login.current_user.is_authenticated:
            return redirect(url_for('.index'))

        self._template_args['form'] = form_

        return super(TrackerAdminResources, self).index()

    @flask_admin.expose('/logout/')
    def logout(self):  # pylint: disable=no-self-use
        flask_login.logout_user()
        return redirect(url_for('.index'))

    @flask_admin.expose('/add_a_working_time_slot', methods=('GET', ))
    @protect
    def add_a_working_time_slot(self):    # pylint: disable=no-self-use

        if not flask_login.current_user.is_authenticated:
            return redirect(url_for('.login'))

        session = MODELS_GLOBAL_CONTEXT['session']

        selected_task_name = request.args.get('selected_task').split('::')[0]
        hours_to_add = request.args.get('hours_to_add')
        current_user = session.query(User).filter(User.id == flask_login.current_user.id).first()
        selected_task = session.query(Task).filter(Task.name == selected_task_name).first()

        data = {
            'duration': float(hours_to_add),
            'user': current_user,
            'task': selected_task,
        }

        wt = WorkTime(**data)
        session.add(wt)
        session.commit()

        url_ = compile_filtered_url('worktime',
                                    [('date', 'greater_than', get_start_of_week()), ('user_user_name', 'equals', current_user.name)])

        return redirect(url_)

    @flask_admin.expose('/report', methods=('GET', 'POST'))
    @protect
    def report_query(self):

        session = MODELS_GLOBAL_CONTEXT['session']
        if request.method == 'GET':

            project_names = [p.name for p in session.query(Project).limit(50)]
            order_names = [o.name for o in session.query(Order).limit(50)]
            user_names = [o.name for o in session.query(User).limit(50)]

            ctx = {
                'projects': project_names,
                'orders': order_names,
                'users': user_names,
                'report_title': 'report 000',
                'report_results': []
            }

            ret = self.render('admin/report.html', **ctx)

        else:

            data = {
                'time_s': time.asctime(),
                'report_title': "",
                'results': [
                ],
            }

            ret = current_app.response_class(
                response=json.dumps(data, indent=2),
                mimetype='application/json'
            )

        return ret

    @flask_admin.expose('/filtered_view', methods=('GET', 'POST'))
    @protect
    def filtered_view(self):          # pylint: disable=no-self-use

        filters = []
        request_args = {}
        for k in request.args:
            v = request.args.getlist(k)
            request_args[k] = v

        model_name = request_args.pop('model_name')[0]
        filters += [(k, 'in_list', v) for k, v in request_args.items()]
        url_ = compile_filtered_url(model_name, filters)
        return redirect(url_)

    @flask_admin.expose('/markdown_to_html', methods=('POST', ))
    @protect
    def markdown_to_html(self):          # pylint: disable=no-self-use

        try:
            content = request.json.get('content')
            msg = markdown.markdown(content)
        except Exception as exc:
            msg = "ERROR: {}".format(exc)
            logging.error(traceback.format_exc())

        ret = current_app.response_class(
            response=Markup(msg),
            mimetype='text')

        return ret


def define_view_classes(app):
    """ we need an already initialized app to (access the app.config), when defining the ModelView classes """

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
            capabilities_map = app.config.get('ROLES_CAPABILITIES_MAP', {})
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
        # ~ can_delete = False

        form_args = {
            'email': {
                'validators': [validators.Email()],
            },
        }

        form_choices = {
            'role': [(k, k) for k in app.config.get('ROLES_CAPABILITIES_MAP', {})],
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
            'followed',
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

        def display_worked_hours(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use

            today = datetime.now().date()
            start_of_the_week = today - timedelta(days=today.weekday())

            total = sum([h.duration for h in obj.worktimes if h.date >= start_of_the_week])
            return Markup("%.2f" % total)

        column_formatters = TrackerModelView.column_formatters.copy()

        column_formatters.update({
            'worktimes': display_worked_hours,
        })

        column_labels = dict(worktimes='Worked Hours in This Week')

    class TaskView(TrackerModelView):     # pylint: disable=unused-variable

        # ~ edit_template = 'admin/edit_task.html'

        # ~ can_delete = False
        # ~ column_details_list = ()

        column_searchable_list = (
            'description',
            'cathegory',
        )

        form_args = {
            'cathegory': {
                'description': app.config.get('CATHEGORY_DESCRIPTION', 'missing description.'),
            },
        }

        form_choices = {
            'department': app.config.get('DEPARTMENTS'),
            'status': app.config.get('TASK_STATUSES'),
            'priority': app.config.get('TASK_PRIORITIES'),
            'cathegory': app.config.get('TASK_CATHEGORIES'),
        }

        column_list = (
            'name',
            'status',
            'milestone',
            'department',
            'order',
            # ~ 'project',
            'priority',
            'cathegory',
            'parent',
            'date_created',
            'assignee',
            'followers',
            'description',
            'worktimes',
        )

        column_editable_list = (
            'assignee',
            'cathegory',
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
            'cathegory',
            'assignee.name',
            # ~ 'project.name',
            'milestone.name',
            'order.name',
        )

        form_columns = (
            'name',
            'description',
            'assignee',
            'status',
            'priority',
            'cathegory',
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

        column_labels = dict(worktimes='Total Worked Hours')

        def display_worked_hours(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use

            total = sum([h.duration for h in obj.worktimes])
            return Markup("%.2f" % total)

        column_formatters = TrackerModelView.column_formatters.copy()

        column_formatters.update({
            'worktimes': display_worked_hours,
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

            ret = super(TaskView, self).on_model_change(form, obj, is_created)

            logging.warning("obj.content:{}".format(obj.content))

            return ret

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


def init_admin(app, db):

    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)

    session = MODELS_GLOBAL_CONTEXT['session']

    # ~ when defining this user_loader, we need an already initialized login_manager
    # ~ and an active db session
    @login_manager.user_loader
    def load_user(user_id):    # pylint: disable=unused-variable
        return session.query(User).get(user_id)

    index_view_ = TrackerAdminResources(url='/')    # pylint: disable=undefined-variable
    admin_ = Admin(app, name='FlaskTracker', template_mode='bootstrap3', index_view=index_view_)

    # ~ we need an already initialized app (to access the app.config), when defining the ModelView classes
    globals().update(define_view_classes(app))

    admin_.add_view(TaskView(Task, db.session))               # pylint: disable=undefined-variable
    admin_.add_view(ProjectView(Project, db.session))         # pylint: disable=undefined-variable
    admin_.add_view(MilestoneView(Milestone, db.session))     # pylint: disable=undefined-variable
    admin_.add_view(OrderView(Order, db.session))             # pylint: disable=undefined-variable
    admin_.add_view(AttachmentView(Attachment, db.session))    # pylint: disable=undefined-variable

    admin_.add_view(TrackerModelView(Customer, db.session, category="admin"))    # pylint: disable=undefined-variable
    admin_.add_view(UserView(User, db.session, category="admin"))    # pylint: disable=undefined-variable
    admin_.add_view(WorkTimeView(WorkTime, db.session, category="admin"))    # pylint: disable=undefined-variable

    admin_.add_link(MenuLink(name='Wiki', url='/wiki/'))

    @app.route('/attachment/<path:filename>')
    def attachment(filename):
        return send_from_directory(app.config['ATTACHMENT_PATH'], filename)

    return admin_
