# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=broad-except

import logging
import traceback
import json
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from werkzeug.security import check_password_hash  # pylint: disable=import-error
from jinja2 import contextfunction   # pylint: disable=import-error
from flask import (Markup, url_for, redirect, request)  # pylint: disable=import-error
from wtforms import form, fields, validators  # pylint: disable=import-error
import flask_login  # pylint: disable=import-error
import markdown2  # pylint: disable=import-error
import flask_admin  # pylint: disable=import-error
from flask_admin.base import Admin     # pylint: disable=import-error
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
    MODELS_GLOBAL_CONTEXT,
    get_package_version)



# ~ helpers (aka Louisiana hoppers with herpes)
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


def define_view_classes(app):

    """ we need an already initialized app to (access the app.config), when defining the ModelView classes """

    class TrackerModelView(ModelView):

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

    class WorkTimeView(TrackerModelView):

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

    class OrderView(TrackerModelView):

        column_editable_list = (
            'customer',
            # ~ 'project',
        )

    class MilestoneView(TrackerModelView):

        column_editable_list = (
            # ~ 'project',
            'start_date',
            'due_date',
        )

        column_filters = (
            'start_date',
            'due_date',
            'tasks',
        )

        column_list = (
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

    class ProjectView(TrackerModelView):

        column_editable_list = (
            # ~ 'milestones',
            # ~ 'orders',
        )

        column_list = (
            'name',
            'description',
        )

    class UserView(TrackerModelView):

        can_create = False
        can_delete = False

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

        column_formatters = TrackerModelView.column_formatters

        column_formatters.update({
            'worktimes': display_worked_hours,
        })

        column_labels = dict(worktimes='Worked Hours in This Week')

    class TaskView(TrackerModelView):

        # ~ can_delete = False

        column_searchable_list = (
            'description',
            'cathegory',
        )

        form_args = {
            'description': {
                'description': 'NOTE: you can use this field also for TAGS {}'.format(app.config.get('TASK_TAGS')),
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
            'order',
            'project',
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
            'date_modified',
            'description',
            'cathegory',
            'assignee.name',
            'order.name',
            # ~ 'order.customer',
            'project.name',
            'milestone.name',
            'status',
            # ~ 'followers',
        )

        form_columns = (
            'name',
            'description',
            'assignee',
            'status',
            'priority',
            'cathegory',
            'project',
            'department',
            'milestone',
            'order',
            'parent',
            'followers',
            'assignee',
            # ~ 'related_tasks',
            # ~ 'content',
        )

        column_labels = dict(worktimes='Total Worked Hours')

        def display_worked_hours(self, context, obj, name):   # pylint: disable=unused-argument, no-self-use

            total = sum([h.duration for h in obj.worktimes])
            return Markup("%.2f" % total)

        column_formatters = TrackerModelView.column_formatters

        column_formatters.update({
            'worktimes': display_worked_hours,
        })

        def get_edit_form(self):

            form_ = super(TaskView, self).get_edit_form()

            cnt_description = 'NOTE: you can use Markdown syntax (https://daringfireball.net/projects/markdown/syntax). Use preview button to see what you get.'
            form_.content = fields.TextAreaField('* content *', [validators.optional(), validators.length(max=1000)],
                                                 description=cnt_description, render_kw={"rows": 12, "style": "background:#fff; border:dashed #bc2122 1px; height:auto;"})

            form_.preview_content_button = fields.BooleanField(u'preview content', [], render_kw={})

            setattr(form_, 'cathegory_tooltip_string', Markup(app.config.get('CATHEGORY_TOOLTIP_STRING')))

            return form_

        @contextfunction
        def get_detail_value(self, context, model, name):
            ret = super().get_detail_value(context, model, name)
            if name == 'content':
                ret = markdown2.markdown(ret)
                ret = Markup(ret)
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
                # ~ flash('NOTE: cannot make task {} parent of itself.'.format(obj.name))
                msg = 'NOTE: cannot make task {} parent of itself.'.format(obj.name)
                raise validators.ValidationError(msg)

            if hasattr(form_, 'status') and form_.status:
                next_ = form_.status.data

                if next_ in ('open', 'in_progress'):
                    if not obj.assignee or obj.assignee.name == 'anonymous':
                        msg = 'task {} must have a known assignee, to be {}.'.format(obj.name, next_)
                        raise validators.ValidationError(msg)

            ret = super(TaskView, self).on_model_change(form, obj, is_created)
            return ret

    class TrackerAdminResources(flask_admin.AdminIndexView):

        @flask_admin.expose("/")
        @flask_admin.expose("/home")
        @flask_admin.expose("/index")
        def index(self, ):

            t0 = time.time()

            if not flask_login.current_user.is_authenticated:
                return redirect(url_for('.login'))

            session = MODELS_GLOBAL_CONTEXT['session']

            start_of_the_week = get_start_of_week()
            start_of_the_month = get_start_of_month()
            user_name = flask_login.current_user.name

            assigned_task_names = ["{}::{}".format(t.name, t.description or "")[:64] for t in session.query(Task).filter(Task.status == 'in_progress').filter(
                Task.assignee_id == flask_login.current_user.id).limit(app.config.get('MAX_OPEN_TASK_PER_USER', 20))]

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

            project_names = sorted([o.name for o in session.query(Project).limit(50) if o.in_progress])
            order_names = sorted([o.name for o in session.query(Order).limit(50) if o.in_progress])
            milestone_names = sorted([o.name for o in session.query(Milestone).limit(50) if o.in_progress])
            user_names = sorted([o.name for o in session.query(User).limit(50)])
            cathegory_names = sorted([ n[0] for n in app.config.get('TASK_CATHEGORIES') ])
            department_names = sorted([ n[0] for n in app.config.get('DEPARTMENTS') ])

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

            # ~ logging.warning("")

            # handle user login
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

        @flask_admin.expose('/gantt', methods=('GET', 'POST'))
        def gantt_page(self):

            logging.warning("request.form:{}".format(request.form))

            ctx = {
                'form': request.form,
            }
            return self.render("admin/gantt_page.html", **ctx)

        @flask_admin.expose('/report', methods=('GET', 'POST'))
        def report_query(self):

            logging.warning("request.args:{}".format(request.args))
            logging.warning("request.form:{}".format(request.form))
            # ~ logging.warning("request.json:{}".format(request.json))
            logging.warning("request.method:{}".format(request.method))

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
                        [time.asctime(), time.asctime(), time.asctime()],
                        [time.asctime(), time.asctime(), time.asctime()],
                        [time.asctime(), time.asctime(), time.asctime()],
                        [time.asctime(), time.asctime(), time.asctime()],
                        [time.asctime(), time.asctime(), time.asctime()],
                        [time.asctime(), time.asctime(), time.asctime()],
                    ],
                }

                ret = app.response_class(
                    response=json.dumps(data, indent=2),
                    mimetype='application/json'
                )

            return ret

        @flask_admin.expose('/filtered_view', methods=('GET', 'POST'))
        def filtered_view(self):          # pylint: disable=no-self-use

            logging.warning("request.args:{}".format(request.args))
            # ~ logging.warning("request.form:{}".format(request.form))

            filters = []
            request_args = {}
            logging.warning("request.args:{}".format(request.args))
            logging.warning("list(request.args):{}".format(list(request.args)))
            for k in request.args:
                v = request.args.getlist(k)
                logging.warning("(k, v):{}".format((k, v)))
                # ~ request_args.setdefault(k, [])
                # ~ request_args[k].append(v)
                request_args[k] = v

            logging.warning("request_args:{}".format(request_args))

            model_name = request_args.pop('model_name')[0]

            filters += [(k, 'in_list', v) for k, v in request_args.items()]

            url_ = compile_filtered_url(model_name, filters)

            logging.warning("url_:{}".format(url_))

            return redirect(url_)

        @flask_admin.expose('/markdown_to_html', methods=('POST', ))
        def markdown_to_html(self):          # pylint: disable=no-self-use

            try:
                # ~ msg = ''
                content = request.json.get('content')
                msg = markdown2.markdown(content)
            except Exception as exc:
                msg = "ERROR: {}".format(exc)
                logging.error(traceback.format_exc())

            ret = app.response_class(
                response=Markup(msg),
                mimetype='text')

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

    # ~ we need an already initialized app (to access the app.config), when defining the ModelView classes
    globals().update(define_view_classes(app))

    index_view_ = TrackerAdminResources(url='/')

    admin_ = Admin(app, name='FlaskTracker', template_mode='bootstrap3', index_view=index_view_)

    admin_.add_view(TaskView(Task, db.session))
    admin_.add_view(ProjectView(Project, db.session))
    admin_.add_view(MilestoneView(Milestone, db.session))
    admin_.add_view(OrderView(Order, db.session))
    admin_.add_view(TrackerModelView(Customer, db.session, category="admin"))
    admin_.add_view(UserView(User, db.session, category="admin"))
    admin_.add_view(WorkTimeView(WorkTime, db.session, category="admin"))

    return admin_
