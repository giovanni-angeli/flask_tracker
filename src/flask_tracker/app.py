# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=broad-except

import os
import sys
import logging

import flask_migrate                 # pylint: disable=import-error

from flask import Flask  # pylint: disable=import-error

from flask_tracker.models import (init_orm, get_package_version)
from flask_tracker.api import init_restless_api
from flask_tracker.admin import init_admin

from flask_tracker.email_client import EMailClient
from flask_tracker.wiki.routes import bp as wiki_blueprint


HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FOLDER = os.path.join(HERE, "templates")
STATIC_FOLDER = os.path.join(HERE, "static")


def set_logging(log_level):
    fmt_ = logging.Formatter('[%(asctime)s]'
                             # ~ '%(name)s:'
                             '%(levelname)s:'
                             '%(funcName)s() '
                             '%(filename)s:'
                             '%(lineno)d: '
                             '%(message)s ')

    ch = logging.StreamHandler()
    ch.setFormatter(fmt_)
    logger_ = logging.getLogger()
    logger_.handlers = []
    logger_.addHandler(ch)
    logger_.setLevel(log_level)


def parse_arg():

    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--config_file', help="path to a file containing the configuration settings. No default")
    options = parser.parse_args(sys.argv[1:])
    return options


def _init_app(argv):

    logging.warning("__file__:{}".format(__file__))

    app = Flask('FlaskTracker', template_folder=TEMPLATE_FOLDER, static_url_path="", static_folder=STATIC_FOLDER)

    sys.argv = argv
    options = parse_arg()
    logging.warning("options.config_file:{}".format(options.config_file))
    app.config.from_pyfile(options.config_file, silent=False)

    set_logging(app.config.get("LOG_LEVEL", logging.WARNING))

    db = init_orm(app)
    init_admin(app, db)


    flask_migrate_ = flask_migrate.Migrate(compare_type=True)
    flask_migrate_.init_app(app, db, render_as_batch=True)

    wiki_blueprint.template_folder = os.path.join(HERE, 'wiki', 'templates')
    app.register_blueprint(wiki_blueprint, url_prefix='/wiki')

    app.app_context().push()

    # cls_models = [mapper.class_ for mapper in db.Model.registry.mappers]
    # for mapper in db.Model.registry.mappers:
    #     logging.warning(mapper.__dict__)

    init_restless_api(app, db)

    # for r in app.url_map.iter_rules():
    #     if 'api' in r.rule:
    #         logging.warning(f'{r.endpoint}: ({r.rule}, {list(r.methods)})')

    return app


def initialize_instance():

    import shutil
    import glob

    dst = sys.argv[1]
    os.makedirs(dst, exist_ok=True)

    for file in glob.glob(os.path.join(HERE, "default_conf", '*.*')):
        logging.warning("copying {} in {}".format(file, dst))
        shutil.copy(file, dst)


def create_email_client(flask_app):

    email_client = None

    EMAIL_CREDENTIALS_PATH = flask_app.config.get('EMAIL_CREDENTIALS_PATH', '----')
    IMAP_HOST_PORT = flask_app.config.get('IMAP_HOST_PORT')
    SMTP_HOST_PORT = flask_app.config.get('SMTP_HOST_PORT')
    CHECK_EMAIL_TIME_STEP = flask_app.config.get('CHECK_EMAIL_TIME_STEP', 60)
    if (os.path.exists(EMAIL_CREDENTIALS_PATH) and IMAP_HOST_PORT and SMTP_HOST_PORT):
        email_client = EMailClient(path_to_credentials=EMAIL_CREDENTIALS_PATH,
                                   imap_host_port=IMAP_HOST_PORT,
                                   smtp_host_port=SMTP_HOST_PORT,
                                   time_step=CHECK_EMAIL_TIME_STEP)

    setattr(flask_app, 'email_client_tracker', email_client)

    return email_client


def main():

    flask_app = _init_app(sys.argv)

    logging.warning("\n\tpackage version:{}\n".format(get_package_version()))

    HOST = flask_app.config.get('HOST')
    PORT = flask_app.config.get('PORT')

    from waitress.server import create_server     # pylint: disable=import-error
    from waitress.wasyncore import poll2          # pylint: disable=import-error

    server = create_server(flask_app, host=HOST, port=PORT)
    logging.warning("serving {} on http://{}:{}".format(flask_app, HOST, PORT))

    email_client = create_email_client(flask_app)
    logging.warning("email_client:{}".format(email_client))

    try:

        timeout = 5.0
        while server._map:                  # pylint: disable=protected-access
            poll2(timeout, server._map)     # pylint: disable=protected-access
            if email_client:
                email_client.poll()
    except (SystemExit, KeyboardInterrupt):

        server.close()
        if email_client:
            email_client.close()


if __name__ == '__main__':

    main()
