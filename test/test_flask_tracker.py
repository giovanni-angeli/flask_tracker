# coding: utf-8

import os
import sys
import logging
import tempfile

import pytest

import flask_tracker

@pytest.fixture
def client():

    here = os.path.dirname(os.path.abspath(__file__))

    argv = '* ' + "-c {}".format(os.path.join(here, '..', 'conf/flask_test_conf.py'))
    argv = argv.split()

    # ~ logging.warning("argv:{}".format(argv))

    app = flask_tracker.app.init_app(argv)

    with app.test_client() as client:
        with app.app_context():
            flask_tracker.models.init_orm(app)
        yield client

def test_index(client):
    """get index page."""
    rv = client.get('/index')

def test_task(client):
    """get task page."""
    rv = client.get('/task')
