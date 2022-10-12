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
        if 'worktimes' in model_dict:
            wtimes = model_dict.get('worktimes')
            model_dict['worktimes'] = sum([float(wt.get('duration')) for wt in wtimes])
        if 'worktimes_claim' in model_dict:
            wtimes = model_dict.get('worktimes_claim')
            model_dict['worktimes_claim'] = sum([float(wt.get('duration')) for wt in wtimes])
    if milestone:
        milestn = model_dict.get('milestone')
        model_dict['milestone'] = milestn.get('name') if milestn else None
        model_dict['project_id'] = milestn.get('project_id') if milestn else None
        projct_id = milestn.get('project_id') if milestn else None
        model_dict['project'] = None
        if projct_id:
            project_db = DB_SESSION.query(flask_tracker.models.Project).filter(flask_tracker.models.Project.id == projct_id).first()
            project = project_db.object_to_dict()
            model_dict['project'] = project.get('name')
            # model_dict['project'] = getattr(project_db, 'name')


    # t_json_str = json.dumps(t_dict, indent = 4)
    date_keys = ['installation_date', 'date_created', 'date_modified', 'start_date', 'due_date']
    for d in date_keys:
        m_dict_date = model_dict.get(d, None)
        if m_dict_date:
            m_dict_date = m_dict_date.split('T')[0] # get only yyyy-mm-dd
            model_dict[d] = m_dict_date

    return model_dict


class TaskApi(Resource):

    def get(self):

        excluded_fields = ['followers', 'description', 'attachments', 'content', 'resources', 'modifications', 'lesson_learned']
        tasks_db = DB_SESSION.query(flask_tracker.models.Task).order_by(flask_tracker.models.Task.date_created.desc())
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


class ClaimApi(Resource):

    def get(self):

        excluded_fields = ['content', 'description', 'lesson_learned', 'modifications', 'followers']
        claims_db = DB_SESSION.query(flask_tracker.models.Claim).order_by(flask_tracker.models.Claim.date_created.desc())
        claims = [frmt_model_obj(c, excluded_fields, include_relationship=1, worktimes=True, milestone=True)
                  for c in claims_db]

        response = {
            "results": claims
        }

        response_json = json.dumps(response, indent = 4)

        return Response(response_json, mimetype="application/json", status=200)


class MilestoneApi(Resource):

    def get(self):

        excluded_fields = ['tasks', 'claims', 'project', 'description']
        milestone_db = DB_SESSION.query(flask_tracker.models.Milestone)
        milestones = [frmt_model_obj(m, excluded_fields).get('name')
                      for m in milestone_db]
        unique_milestones = list(set(milestones))

        response = {
            "results": unique_milestones
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
    _api.add_resource(ClaimApi, URL_PREFIX + 'claim')
    _api.add_resource(ProjectApi, URL_PREFIX + 'project')
    _api.add_resource(MilestoneApi, URL_PREFIX + 'milestone')
