# flask_tracker
a simple activity tracker based on Flask Admin (https://flask-admin.readthedocs.io).

flask_tracker is a variation on the theme of activity trackers (Trac, Redmine, Assembla, Trello, ...), based on a home-made approach in order to get:
* total control, versatilty and customability.
* no overhead i.e. *lightweight*
* much fun.

It is not aimed to be:
* a full-optional team-management-tool for large companies
* a full-fledged, full-optional spaceship

It is buitl using (see INSTALL_REQUIRES in setup.py fpr a complete dependency list):

    'flask',
    'flask_admin',
    'flask_sqlalchemy',
    'waitress',  # WSGI server (https://docs.pylonsproject.org/projects/waitress)
    'flask-login',
    'markdown2',


# flask_tracker:

### Overview.

set working paths:

    $ export FT_PROJECT_ROOT=<your-project-sources-path>
    $ export FT_RUNDATA_ROOT=<your-project-data-path>
    $ export FT_VENV_ROOT=<your-virtualenv-root-path>

create virtualenv:

    $ virtualenv -p /usr/bin/python3 ${FT_VENV_ROOT}

build:

    $ (cd ${FT_PROJECT_ROOT} && python3 setup.py bdist_wheel --dist-dir ./__wheels__)

install:

    $ (. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT} && pip install .)

OR install in edit mode, i.e. development mode:

    $ (. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT} && pip install -e .)

run:

    $ ${FT_VENV_ROOT}/bin/flask_tracker -c ${FT_PROJECT_ROOT}/conf/flask_conf.py

