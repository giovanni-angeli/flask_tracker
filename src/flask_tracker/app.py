# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=broad-except

import os
import sys
import logging
import traceback

from flask import Flask                    # pylint: disable=import-error

from flask_tracker.models import init_db
from flask_tracker.admin import init_admin


here = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FOLDER = os.path.join(here, "templates")

def set_logging(log_level):
    fmt_ = logging.Formatter('[%(asctime)s]'
                             '%(name)s:'
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


def init_app():

    # ~ app = Flask('FlaskTracker', template_folder='./templates')
    app = Flask('FlaskTracker', template_folder=TEMPLATE_FOLDER)

    options = parse_arg()
    logging.warning("options.config_file:{}".format(options.config_file))
    app.config.from_pyfile(options.config_file, silent=False)

    set_logging(app.config.get("LOG_LEVEL", logging.WARNING))

    db, session = init_db(app)
    init_admin(app, db)

    app._static_folder = os.path.join(here, 'static')
    logging.warning("app._static_folder:{}".format(app._static_folder))

    return app


def main():

    flask_app = init_app()

    HOST = flask_app.config.get('HOST')
    PORT = flask_app.config.get('PORT')
    logging.warning("start serving admin UI on http://{}:{}".format(HOST, PORT))
    if flask_app.config.get('ENV') == 'production':

        from waitress import serve      # pylint: disable=import-error
        serve(flask_app, host=HOST, port=PORT)

    else:

        flask_app.run(host=HOST, port=PORT)


if __name__ == '__main__':

    main()
