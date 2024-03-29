# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation, consider-using-f-string, logging-fstring-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=broad-except

import logging
import traceback
import json
import time
import os
from datetime import datetime, timedelta
from urllib.parse import quote
from functools import wraps

import markdown  # pylint: disable=import-error
from werkzeug.security import check_password_hash  # pylint: disable=import-error
from werkzeug.utils import secure_filename # pylint: disable=import-error
from flask import (Markup, url_for, redirect, request, current_app, send_from_directory, jsonify)  # pylint: disable=import-error
from wtforms import (form, fields, validators)  # pylint: disable=import-error
from isoweek import Week          # pylint: disable=import-error

import flask_login  # pylint: disable=import-error
import flask_admin  # pylint: disable=import-error
from flask_admin.base import Admin, MenuLink    # pylint: disable=import-error

from flask_tracker.models import (
    Task,
    Project,
    Milestone,
    Customer,
    Order,
    User,
    WorkTime,
    WorkTimeClaim,
    Attachment,
    History,
    Claim,
    Improvement,
    Registry,
    MODELS_GLOBAL_CONTEXT,
    get_package_version)

from flask_tracker.admin_views import define_view_classes, has_capabilities


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

    # ~ /task/?flt1_project_name_contains=lask
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


def check_login(f):
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

        # ~ logging.warning("self.login.data:{}".format(self.login.data))

        user = self.get_user()

        # ~ logging.warning("user:{}, field:{}".format(user, field))

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

    @staticmethod
    def __get_working_time_edit_form_url(request_args, model='Task'):
        session = MODELS_GLOBAL_CONTEXT['session']
        model_klass = eval(model)   #pylint: disable=eval-used
        id_ = request_args.get('id', None)

        if id_ is not None:
            selected_model = session.query(model_klass).filter(model_klass.id == id_).first()
            hours_to_add = 0
            date_ = datetime.now().date().isoformat()
        else:
            selected_task_name = request_args.get('selected_task').split('::')[0]
            selected_model = session.query(Task).filter(Task.name == selected_task_name).first()
            hours_to_add = request_args.get('hours_to_add')
            date_ = request_args.get('date')

        current_user = session.query(User).filter(User.id == flask_login.current_user.id).first()

        toks = [int(i) for i in date_.split('-')] + [9, 0]
        date_local_ = datetime(*toks)
        date_utc_ = date_local_ + timedelta(seconds=time.timezone)
        logging.warning("date_:{}, date_local_:{}, date_utc_:{}".format(date_, date_local_, date_utc_))

        data = {
            'duration': float(hours_to_add),
            'user': current_user,
            'date_created': date_utc_,
            model.lower(): selected_model,
        }
        # logging.warning(f'data > {data}')

        worktime_map = {
            'Task' : (WorkTime, 'worktime'),
            'Claim' : (WorkTimeClaim, 'worktimeclaim'),
        }

        wt_cls = worktime_map.get(model)[0]
        wt = wt_cls(**data)
        session.add(wt)
        session.commit()

        wt_url = worktime_map.get(model)[1]
        url_ = "/{1}/edit/?id={0}".format(wt.id, wt_url)
        url_ = quote(url_, safe='/?&=+')

        return url_

    @flask_admin.expose("/")
    @flask_admin.expose("/home")
    @flask_admin.expose("/index")
    @check_login
    def index(self, ):

        # ~ t0 = time.time()

        session = MODELS_GLOBAL_CONTEXT['session']

        if flask_login.current_user.role == 'service':
            self._template = "/admin/index_service.html"  # pylint: disable=attribute-defined-outside-init

            claim_filtered_views = [
                ('open claims', compile_filtered_url('claim', [('status', 'equals', 'open')])),
                ('claims not closed nor invalid', compile_filtered_url(
                    'claim', [('status', 'not_in_list', ('closed', 'invalid'))])),
            ]

            ctx = {
                'supervisor_web_port': current_app.config.get('SUPERVISOR_WEB_PORT', 0),
                'claim_filtered_views': claim_filtered_views,
            }

        else:
            self._template = "/admin/index.html"   # pylint: disable=attribute-defined-outside-init
            start_of_the_month = get_start_of_month()
            user_name = flask_login.current_user.name

            MAX_OPEN_TASK_PER_USER = current_app.config.get('MAX_OPEN_TASK_PER_USER', 20)
            TASK_CATEGORIES = current_app.config.get('TASK_CATEGORIES', [])
            DEPARTMENTS = current_app.config.get('DEPARTMENTS', [])

            # ~ logging.warning("TASK_CATEGORIES:{}".format(TASK_CATEGORIES))

            assigned_task_names = ["{}::{}".format(t.name, t.description or "")[:64] for t in session.query(Task).filter(Task.status == 'in_progress').filter(
                Task.assignee_id == flask_login.current_user.id).limit(MAX_OPEN_TASK_PER_USER)]

            task_filtered_views = [
                ('all open tasks', compile_filtered_url('task', [('status', 'equals', 'open')])),
                ('all tasks in progress', compile_filtered_url('task', [('status', 'equals', 'in_progress')])),
                ('all tasks followed by <b>{}</b>'.format(user_name),
                 compile_filtered_url('task', [('followers_user_name', 'contains', user_name)])),
                ('tasks assigned to <b>{}</b> not closed nor invalid'.format(user_name),
                 compile_filtered_url('task', [('assignee_user_name', 'equals', user_name), ('status', 'not_in_list', ('closed', 'invalid'))])),
                ('all tasks assigned to <b>{}</b>'.format(user_name),
                 compile_filtered_url('task', [('assignee_user_name', 'equals', user_name)])),
            ]

            worktime_filtered_views = [
                ('hours worked by <b>{}</b>, in this month'.format(user_name),
                 compile_filtered_url('worktime', [('date', 'greater_than', start_of_the_month), ('user_user_name', 'equals', user_name)])),
            ]

            project_names = sorted([o.name for o in session.query(Project).limit(50)])
            order_names = sorted([o.name for o in session.query(Order).limit(50) if o.in_progress])
            milestone_names = sorted([o.name for o in session.query(Milestone).limit(50) if o.in_progress])
            user_names = sorted([o.name for o in session.query(User).limit(50)])
            category_names = sorted([n[0] for n in TASK_CATEGORIES])
            department_names = sorted([n[0] for n in DEPARTMENTS])

            can_add_task_and_worktime = has_capabilities(current_app, flask_login.current_user, 'task', operation='c')
            can_add_task_and_worktime = can_add_task_and_worktime and has_capabilities(
                current_app, flask_login.current_user, 'work_time', operation='c')

            t_ = datetime.now().date().isocalendar()
            week = "{:4d}-W{:02d}".format(t_[0], t_[1])

            ctx = {
                'projects': project_names,
                'orders': order_names,
                'milestones': milestone_names,
                'users': user_names,
                'categories': category_names,
                'departments': department_names,
                'time': time.asctime(),
                'week': week,
                'version': get_package_version(),
                'assigned_task_names': assigned_task_names,
                'task_filtered_views': [(Markup("{}. {}".format(i, view[0])), view[1]) for i, view in enumerate(task_filtered_views)],
                'worktime_filtered_views': [(Markup("{}. {}".format(i, view[0])), view[1]) for i, view in enumerate(worktime_filtered_views)],
                'supervisor_web_port': current_app.config.get('SUPERVISOR_WEB_PORT', 0),
                'can_add_task_and_worktime': can_add_task_and_worktime,
            }

        return self.render(self._template, **ctx)

    @flask_admin.expose('/login/', methods=('GET', 'POST'))
    def login(self):

        form_ = LoginForm(request.form)
        if flask_admin.helpers.validate_form_on_submit(form_):
            user = form_.get_user()
            flask_login.login_user(user)
            logging.warning("user.name:{}".format(user.name))

            logging.warning("current_user:{}".format(flask_login.current_user))

        if flask_login.current_user.is_authenticated:
            return redirect(url_for('.index'))

        self._template_args['form'] = form_

        return super().index()

    @flask_admin.expose('/logout/')
    def logout(self):  # pylint: disable=no-self-use
        logging.warning("current_user:{}".format(flask_login.current_user))
        flask_login.logout_user()
        return redirect(url_for('.index'))

    @flask_admin.expose('/add_a_working_time_slot', methods=('GET', ))
    @check_login
    def add_a_working_time_slot(self):    # pylint: disable=no-self-use

        redirect_url = self.__get_working_time_edit_form_url(
            request_args=request.args,
        )

        return redirect(redirect_url)

    @flask_admin.expose('/add_a_working_claim_time_slot', methods=('GET', ))
    @check_login
    def add_a_working_claim_time_slot(self):    # pylint: disable=no-self-use

        redirect_url = self.__get_working_time_edit_form_url(
            request_args=request.args,
            model='Claim',
        )

        return redirect(redirect_url)

    @flask_admin.expose('/report', methods=('GET', 'POST'))
    @check_login
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
    @check_login
    def filtered_view(self):          # pylint: disable=no-self-use

        filters = []
        request_args = {}
        for k in request.args:
            v = request.args.getlist(k)
            request_args[k] = v

        model_name = request_args.pop('model_name')[0]
        if model_name == 'task':
            filters += [(k, 'in_list', v) for k, v in request_args.items()]
        elif model_name == 'worktime':
            def __(k):
                ret = "_".join(k.split('_')[1:]) if k != 'task' else k
                logging.warning("k:{}, ret:{}".format(k, ret))
                return ret
            filters += [(__(k), 'in_list', v) for k, v in request_args.items()]

        url_ = compile_filtered_url(model_name, filters)

        return redirect(url_)

    @flask_admin.expose('/markdown_to_html', methods=('POST', ))
    @check_login
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

        logging.warning("ret:{}".format(ret))
        return ret

    @flask_admin.expose('/view_hours_of_week', methods=('GET', ))
    @check_login
    def view_hours_of_week(self, ):          # pylint: disable=no-self-use
        # ~ logging.warning("request.args:{}".format(request.args))
        # ~ flash("request.args:{}".format(request.args))
        # ~ 'selected_week', '2020-W05'
        selected_week = request.args.get('selected_week')
        year, week_n = selected_week.split('-W')
        w_start = Week(int(year), int(week_n))
        t0 = w_start.monday().isoformat()
        t1 = (w_start + 1).monday().isoformat()
        # ~ admin.py:340: t0:2020-01-27, t1:2020-02-03
        # ~ /worktime/?flt1_user_user_name_equals=Giovanni%20A
        # ~ &flt2_date_between=2020-01-27+00%3A00%3A00+to+2020-02-03+23%3A59%3A59
        url_ = compile_filtered_url('worktime', [
            ('date', 'between', '{}+00:00:00+to+{}+00:00:00'.format(t0, t1)),
            ('user_user_name', 'equals', flask_login.current_user.name),
        ])
        # ~ logging.warning("t0:{}, t1:{}".format(t0, t1))
        # ~ logging.warning("url_:{}".format(url_))
        return redirect(url_)

    @flask_admin.expose('/task_search/<string:key>/', methods=('GET', ))
    @check_login
    def task_search(self, key):          # pylint: disable=no-self-use
        url_ = "/task/?search={}".format(key)
        return redirect(url_)

    @flask_admin.expose('/admin_upload_attachments', methods=('POST', ))
    @check_login
    def upload_attachments(self, ):     # pylint: disable=no-self-use

        resp = {}

        if request.method == 'POST':
            logging.warning('this request is a POST')
            files = request.files.getlist('file[]')
            logging.warning(f'files >> {files}')

            session = MODELS_GLOBAL_CONTEXT['session']
            _id = None
            _model = None
            if hasattr(request, 'form'):

                _id = request.form.get('id', None)
                _model = request.form.get('model', None)

                map_attch_attr = {
                    'task': 'attached_id',
                    'claim': 'claimed_id',
                    'improvement': 'improved_id',
                }

                try:
                    html_response = ''
                    for file in files:
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(current_app.config.get('ATTACHMENT_PATH'), filename))
                        logging.warning(f"created file {filename} on {current_app.config.get('ATTACHMENT_PATH')}")
                        logging.debug(f'model {_model} - {_id}')

                        attch_kwargs = {
                            'name':filename,
                            map_attch_attr[_model]: _id
                        }

                        attch = Attachment(**attch_kwargs)
                        session.add(attch)
                        session.commit()
                        logging.warning(f'Attachment {attch} created on db.')

                        file_url = url_for('attachment', filename=filename)
                        elem = '<a class="form-control" href="' + f"{file_url}" + f'"> [{filename}]({file_url}) </a> '
                        html_response += Markup(elem)

                    resp = jsonify({
                        'message' : 'File(s) uploaded successfully!',
                        'html_response': html_response
                    })
                    resp.status_code = 201

                except Exception as e:
                    logging.error(e)
                    logging.error(traceback.format_exc())
                    resp = jsonify({
                        'message' : f'{traceback.format_exc()}',
                    })
                    resp.status_code = 500

        return resp


def init_admin(app, db):    # pylint: disable=too-many-statements

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

    admin_.add_view(ClaimView(Claim, db.session))               # pylint: disable=undefined-variable

    admin_.add_view(ImprovementView(Improvement, db.session))               # pylint: disable=undefined-variable
    admin_.add_view(RegistryView(Registry, db.session))               # pylint: disable=undefined-variable

    admin_.add_view(TrackerModelView(Customer, db.session, category="admin"))    # pylint: disable=undefined-variable
    admin_.add_view(HistoryView(History, db.session, category="admin"))    # pylint: disable=undefined-variable
    admin_.add_view(UserView(User, db.session, category="admin"))    # pylint: disable=undefined-variable
    admin_.add_view(WorkTimeView(WorkTime, db.session, category="admin"))    # pylint: disable=undefined-variable
    admin_.add_view(WorkTimeClaimView(WorkTimeClaim, db.session, category="admin")) # pylint: disable=undefined-variable

    admin_.add_link(MenuLink(name='Wiki', url='/wiki/'))

    @app.route('/attachment/<path:filename>')
    def attachment(filename):               # pylint: disable=unused-variable
        return send_from_directory(app.config['ATTACHMENT_PATH'], filename)

    return admin_
