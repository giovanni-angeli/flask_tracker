# flask_tracker
a sample activity tracker based on Flask Admin 
(https://flask-admin.readthedocs.io) 
and using markitup 
(https://markitup.jaysalvat.com)

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

