#~ set handy environment variables
#~ source me to use them all
export PYTHONDONTWRITEBYTECODE=1
export FT_PROJECT_ROOT=/opt/PROJECTS/flask_tracker
export FT_RUNCONF_ROOT=/opt/flask_tracker/conf
export FT_VENV_ROOT=/opt/flask_tracker/venv
export | grep FT_
mkdir -p ${FT_PROJECT_ROOT}
mkdir -p ${FT_RUNCONF_ROOT}
mkdir -p ${FT_VENV_ROOT}
alias ft_create_virtenv="virtualenv -p /usr/bin/python3 ${FT_VENV_ROOT}"
alias ft_build="(cd ${FT_PROJECT_ROOT} && python3 setup.py bdist_wheel --dist-dir ./__wheels__)"
alias ft_install="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT} && pip install .)"
alias ft_install_e="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT} && pip install -e .)"
alias ft_init="cp -a ${FT_PROJECT_ROOT}/conf/flask_conf.py ${FT_RUNCONF_ROOT}/ "
alias ft_run="${FT_VENV_ROOT}/bin/flask_tracker -c ${FT_RUNCONF_ROOT}/flask_conf.py"
