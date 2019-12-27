#~ I am useful for development,
#~ I set handy variables into environment. 
#~ Source me to use them all
export PYTHONDONTWRITEBYTECODE=1
export FT_PROJECT_ROOT=/opt/PROJECTS/flask_tracker
export FT_RUNCONF_ROOT=/opt/flask_tracker/conf
export FT_VENV_ROOT=/opt/flask_tracker/venv
export | grep FT_
mkdir -p ${FT_RUNCONF_ROOT}
mkdir -p ${FT_VENV_ROOT}
alias ft_create_virtenv="virtualenv -p /usr/bin/python3 ${FT_VENV_ROOT}"
alias ft_build_w="(cd ${FT_PROJECT_ROOT} && python3 setup.py bdist_wheel --dist-dir ./__wheels__)"
alias ft_build_d="(cd ${FT_PROJECT_ROOT} && python3 setup.py sdist bdist_wheel)"
alias ft_install="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT} && pip install .)"
alias ft_install_e="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT} && pip install -e .)"
alias ft_init="${FT_VENV_ROOT}/bin/flask_tracker_init ${FT_RUNCONF_ROOT}"
alias ft_run="${FT_VENV_ROOT}/bin/flask_tracker_run -c ${FT_RUNCONF_ROOT}/flask_conf.py"
alias ft_twine_test_dist="(cd ${FT_PROJECT_ROOT} && twine check dist/*)"
alias ft_twine_upload_test="(cd ${FT_PROJECT_ROOT} && twine upload --repository-url https://test.pypi.org/legacy/ dist/*)"
alias ft_twine_upload="(cd ${FT_PROJECT_ROOT} && twine upload dist/*)"
