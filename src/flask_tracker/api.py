# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=broad-except
# pylint: disable=logging-fstring-interpolation, consider-using-f-string

import logging
# import traceback
import json

import flask_tracker.models

from flask_restful import Resource, Api # pylint: disable=import-error
from flask import Response              # pylint: disable=import-error

URL_PREFIX = '/api/v1/'
DB_SESSION = None


def frmt_model_obj(model_obj, excluded_fields, 
        include_relationship=0, worktimes=False, milestone=False):
    model_json_str = model_obj.object_to_json(
        include_relationship=include_relationship,
        excluded_fields=excluded_fields
    )

    model_dict = json.loads(model_json_str)
    if worktimes:
        wtimes = model_dict.get('worktimes')
        model_dict['worktimes'] = sum([float(wt.get('duration')) for wt in wtimes])
    if milestone:
        milestn = model_dict.get('milestone')
        model_dict['milestone'] = milestn.get('name') if milestn else None
        model_dict['project_id'] = milestn.get('project_id') if milestn else None
    # t_json_str = json.dumps(t_dict, indent = 4)

    return model_dict


class TaskApi(Resource):

    def get(self):

        excluded_fields = ['followers', 'description', 'attachments', 'content', 'resources', 'modifications', 'lesson_learned']
        tasks_db = DB_SESSION.query(flask_tracker.models.Task)
        tasks = [frmt_model_obj(t, excluded_fields, include_relationship=1, worktimes=True, milestone=True)
                 for t in tasks_db]
        logging.warning(f'tasks({type(tasks)})')

        response = {
            "results": tasks
        }

        response_json = json.dumps(response, indent = 4)

        return Response(response_json, mimetype="application/json", status=200)


class ProjectApi(Resource):

    def get(self):

        projects_db = DB_SESSION.query(flask_tracker.models.Project)
        projects = [frmt_model_obj(p, [])
                 for p in projects_db]
        logging.warning(f'projects({type(projects)})')

        response = {
            "results": projects
        }

        response_json = json.dumps(response, indent = 4)

        return Response(response_json, mimetype="application/json", status=200)


def init_restless_api(app, db):

    # creating APIs using flask_restful library
    _api = Api(app)

    global DB_SESSION               # pylint: disable=global-statement
    if DB_SESSION is None:
        DB_SESSION = db.session

    _api.add_resource(TaskApi, URL_PREFIX + 'task')
    _api.add_resource(ProjectApi, URL_PREFIX + 'project')
