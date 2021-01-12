# flask_tracker

Copyright (c) 2019 2020 giovanni.angeli6@gmail.com

'Development Status :: 2 - Pre-Alpha'

a **very** simplified activity-tracker based on [Flask Admin](https://flask-admin.readthedocs.io).

**flask_tracker** is a variation on the theme of activity trackers (Trac, Redmine, Assembla, Trello, ...), based on a home-made approach in order to get:

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
    'flask-login',
    'markdown',
    'waitress',

___________________________

For the built-in wiki, **flask_tracker** integrates code cloned from the project [alexanderjulo/wiki](https://github.com/alexanderjulo/wiki)

___________________________

### Overview.

set working paths:

    $ export FT_PROJECT_ROOT=/opt/PROJECTS/flask_tracker
    $ export FT_RUNCONF_ROOT=/opt/flask_tracker/conf
    $ export FT_VENV_ROOT=/opt/flask_tracker/venv

create virtualenv:

    $ virtualenv -p /usr/bin/python3 ${FT_VENV_ROOT}

build:

    $ (cd ${FT_PROJECT_ROOT} && python3 setup.py bdist_wheel --dist-dir ./__wheels__)

install:

    $ (. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT} && pip install .)

OR install in edit mode, i.e. development mode:

    $ (. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT} && pip install -e .)

init the application (i.e. clone default conf files):

    $ ${FT_VENV_ROOT}/bin/flask_tracker_init ${FT_RUNCONF_ROOT}

edit your conf file:

    $ <your-preferred-code-editor> ${FT_RUNCONF_ROOT}/flask_conf.py

run the server:

    $ ${FT_VENV_ROOT}/bin/flask_tracker -c ${FT_RUNCONF_ROOT}/flask_conf.py

open the browser:

    $ firefox <conf-host>:<conf-port>
    
login as: 

    admin, admin

## graph of the db schema (v7):

<img src="/doc/tracker.v7.sqlite.svg" alt="db schema" style="width: 640px;"/>
