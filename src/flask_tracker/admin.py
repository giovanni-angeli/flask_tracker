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

from datetime import datetime, timezone, timedelta

from flask import (Markup, url_for, redirect, request)  # pylint: disable=import-error

from werkzeug.security import check_password_hash  # pylint: disable=import-error

from jinja2 import contextfunction   # pylint: disable=import-error

from wtforms import form, fields, validators  # pylint: disable=import-error

import flask_admin  # pylint: disable=import-error
from flask_admin.base import Admin     # pylint: disable=import-error
from flask_admin.contrib.sqla import ModelView  # pylint: disable=import-error

import flask_login  # pylint: disable=import-error

import markdown2  # pylint: disable=import-error

from flask_tracker.models import (
    Task,
    Project,
    Milestone,
    Customer,
    Order,
    User,
    WorkTime,
    MODELS_GLOBAL_CONTEXT,)




class LoginForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

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


def init_admin(app, db):

    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):    # pylint: disable=unused-variable
        # ~ logging.warning("user_id:{}".format(user_id))
        session = MODELS_GLOBAL_CONTEXT['session']
        return session.query(User).get(user_id)

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

            ret = False
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


        def update_model(self, form_, obj):

            return super().update_model(form_, obj)


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
            'due_date',
        )


    class ProjectView(TrackerModelView):

        column_editable_list = (
            # ~ 'milestones',
            # ~ 'orders',
        )

        column_list = (
            'name',
            'tasks',
            # ~ 'milestones',
            # ~ 'orders',
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

        def display_worked_hours(self, context, obj, name):   # pylint: disable=unused-argument

            today = datetime.now().date()
            start_of_the_week = today - timedelta(days=today.weekday())

            total = sum([h.duration for h in obj.worktimes if h.date_modified >= start_of_the_week])
            return Markup("%.2f" % total)

        column_formatters = TrackerModelView.column_formatters

        column_formatters.update({
            'worktimes': display_worked_hours,
        })

        column_labels = dict(worktimes='Worked Hours in This Week')


    class TaskView(TrackerModelView):

        # ~ can_delete = False

        form_args = {
            'status': {
                'description': 'NOTE: forbidden status transitions:{}'.format(
                    app.config.get('TASK_STATUSES_FORBIDDEN_TRANSITIONS')
                ),
            },
        }

        form_choices = {
            'department': app.config.get('DEPARTMENTS'),
            'status': app.config.get('TASK_STATUSES'),
            'priority': app.config.get('TASK_PRIORITIES'),
        }

        column_list = (
            'name',
            'status',
            'milestone',
            'order',
            'project',
            'priority',
            'parent',
            'date_created',
            'assignee',
            'followers',
            'description',
            'worktimes',
        )

        column_editable_list = (
            'assignee',
            'priority',
            'followers',
            'status',
        )

        column_filters = (
            'name',
            'date_modified',
            'description',
            'assignee.name',
            'order.name',
            'order.customer',
            'milestone.name',
            'status',
            'followers',
        )

        form_columns = (
            'name',
            'description',
            'assignee',
            'status',
            'priority',
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

        def display_worked_hours(self, context, obj, name):   # pylint: disable=unused-argument

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
                                                 description=cnt_description, render_kw={'rows': '16'})
            form_.preview_content_button = fields.BooleanField(u'preview content', [], render_kw={'width': '1600'})

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
                prev_ = form_.status.object_data
                next_ = form_.status.data

                if next_ in ('open', 'in_progress'):
                    if not obj.assignee or obj.assignee.name == 'anonymous':
                        # ~ flash('task {} must have an assignee, to be {}.'.format(obj.name, next_), 'error')
                        msg = 'task {} must have a known assignee, to be {}.'.format(obj.name, next_)
                        raise validators.ValidationError(msg)

            ret = super(TaskView, self).on_model_change(form, obj, is_created)
            return ret


    class TrackerAdminResources(flask_admin.AdminIndexView):

        app = None

        @flask_admin.expose("/")
        @flask_admin.expose("/home")
        @flask_admin.expose("/index")
        def index(self, ):

            if not flask_login.current_user.is_authenticated:
                return redirect(url_for('.login'))

            # ~ url_ = "/task/?flt2_assignee_user_name_equals={}".format(flask_login.current_user.name)
            # ~ return redirect(url_)

            session = MODELS_GLOBAL_CONTEXT['session']

            logging.warning("self._template:{}".format(self._template))

            today = datetime.now().date()
            start_of_the_week = today - timedelta(days=today.weekday())
            start_of_the_week = start_of_the_week.strftime("%Y-%m-%d+00:00:00")
            start_of_the_week = Markup(start_of_the_week)

            start_of_the_month = today - timedelta(days=today.day)
            start_of_the_month = start_of_the_month.strftime("%Y-%m-%d+23:59:00")
            start_of_the_month = Markup(start_of_the_month)

            user_name = flask_login.current_user.name

            assigned_task_names = ["{}::{}".format(t.name, t.description or "")[:64] for t in session.query(Task).filter(Task.status == 'in_progress').filter(
                Task.assignee_id == flask_login.current_user.id).limit(app.config.get('MAX_OPEN_TASK_PER_USER', 20))]

            filtered_views = [
                ('all tasks in progress',
                 '/task/?flt0_status_equals=in_progress'),
                ('tasks followed by <b>{}</b>'.format(user_name),
                 '/task/?flt2_user_name_equals={}'.format(user_name)),
                ('tasks assigned to <b>{}</b>'.format(user_name),
                 '/task/?flt2_assignee_user_name_equals={}'.format(user_name)),
                ('open tasks assigned to <b>{}</b>'.format(user_name),
                 '/task/?flt0_status_equals=open&flt3_assignee_user_name_equals={}'.format(user_name)),
                # ~ ('2. open or in progress tasks assigned to <b>{}</b>'.format(user_name),
                # ~ '/task/?flt3_status_in_list=open%2Cin_progress&flt1_assignee_user_name_equals={}'.format(user_name)),
                ('tasks assigned to <b>{}</b>, in progress'.format(user_name),
                 '/task/?flt0_status_equals=in_progress&flt3_assignee_user_name_equals={}'.format(user_name)),
                ('hours worked by <b>{}</b>, in this week'.format(user_name),
                 '/worktime/?flt2_date_greater_than={}&flt6_user_user_name_equals={}'.format(start_of_the_week, user_name)),
                ('hours worked by <b>{}</b>, in this month'.format(user_name),
                 '/worktime/?flt2_date_greater_than={}&flt6_user_user_name_equals={}'.format(start_of_the_month, user_name)),
            ]

            ctx = {
                'assigned_task_names': assigned_task_names,
                'filtered_views': [(Markup("{}. {}".format(i, view[0])), view[1]) for i, view in enumerate(filtered_views)]
            }
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
        def add_a_working_time_slot(self):

            if not flask_login.current_user.is_authenticated:
                return redirect(url_for('.login'))

            session = MODELS_GLOBAL_CONTEXT['session']

            selected_task_name = request.args.get('selected_task').split('::')[0]
            hours_to_add = request.args.get('hours_to_add')
            current_user = session.query(User).filter(User.id == flask_login.current_user.id).first()
            selected_task = session.query(Task).filter(Task.name == selected_task_name).first()

            data = {
                'date_created': datetime.utcnow(),
                'date_modified': datetime.utcnow(),
                'duration': float(hours_to_add),
                'user': current_user,
                'task': selected_task,
            }

            wt = WorkTime(**data)
            session.add(wt)
            session.commit()

            today = datetime.now().date()
            start_of_the_week = today - timedelta(days=today.weekday())
            start_of_the_week = start_of_the_week.strftime("%Y-%m-%d+00:00:00")
            start_of_the_week = Markup(start_of_the_week)

            url = '/worktime/?flt2_date_greater_than={}&flt6_user_user_name_equals={}'.format(
                start_of_the_week, current_user.name)
            return redirect(url)


        @flask_admin.expose('/report', methods=('GET', ))
        def report(self):

            ctx = {
                'results': {}
            }
            return self.render('admin/report.html', **ctx)

        @flask_admin.expose('/markdown_to_html', methods=('POST', ))
        def markdown_to_html(self):

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
