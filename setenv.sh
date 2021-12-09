#~ I am useful for development,
#~ I set handy variables into environment. 
#~ Source me to use them all
export PYTHONDONTWRITEBYTECODE=1

#~ export FT_PROJECT_ROOT=/mnt/dati/flask_tracker/PROJECT/flask_tracker
#~ export FT_RUNCONF_ROOT=/mnt/dati/flask_tracker
#~ export FT_VENV_ROOT=/mnt/dati/flask_tracker/venv
export FT_PROJECT_ROOT=/opt/PROJECTS/flask_tracker
export FT_RUNCONF_ROOT=/opt/flask_tracker/conf
export FT_VENV_ROOT=/opt/flask_tracker/venv
export FLASK_APP="app:_init_app(['${FT_VENV_ROOT}/bin/flask_tracker_run' , '-c', '${FT_RUNCONF_ROOT}/flask_conf.py'])"


export | grep FT_
export | grep _APP
mkdir -p ${FT_RUNCONF_ROOT}
mkdir -p ${FT_VENV_ROOT}
alias ft_create_virtenv="virtualenv -p /usr/bin/python3 ${FT_VENV_ROOT}"
alias ft_activate=". ${FT_VENV_ROOT}/bin/activate"
alias ft_build_w="(cd ${FT_PROJECT_ROOT} && python3 setup.py bdist_wheel --dist-dir ./__wheels__)"
alias ft_build_d="(cd ${FT_PROJECT_ROOT} && python3 setup.py sdist bdist_wheel)"
alias ft_install="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT} && pip install .)"
alias ft_install_e="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT} && pip install -e .)"
alias ft_init="${FT_VENV_ROOT}/bin/flask_tracker_init ${FT_RUNCONF_ROOT}"
alias ft_run=". ${FT_VENV_ROOT}/bin/activate && ${FT_VENV_ROOT}/bin/flask_tracker_run -c ${FT_RUNCONF_ROOT}/flask_conf.py"
alias ft_twine_test_dist="(cd ${FT_PROJECT_ROOT} && twine check dist/*)"
alias ft_twine_upload_test="(cd ${FT_PROJECT_ROOT} && twine upload --repository-url https://test.pypi.org/legacy/ dist/*)"
alias ft_twine_upload="(cd ${FT_PROJECT_ROOT} && twine upload dist/*)"
alias ft_source_code="ft_activate && cd ${FT_PROJECT_ROOT}/src/flask_tracker"
alias ft_migrate_init="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT}/src/flask_tracker && flask db init)"
# alias ft_migrate_migrate="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT}/src/flask_tracker && flask db migrate)"
alias ft_migrate_migrate=migrate_init
alias ft_migrate_upgrade="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT}/src/flask_tracker && flask db upgrade)"
alias ft_migrate_downgrade="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT}/src/flask_tracker && flask db downgrade)"
alias ft_migrate_history="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT}/src/flask_tracker && flask db history)"

migrate_init() {
	arg="$1"
	msg="$2"
	init_message="$arg '$msg'"
	cmd_migrate="(. ${FT_VENV_ROOT}/bin/activate && cd ${FT_PROJECT_ROOT}/src/flask_tracker && flask db migrate ${init_message})"
	if [[ -z "$arg" ]]; then
		"$cmd_migrate"
	elif [[ "$arg" == '--message' ]] && [[ -n "$msg" ]]; then
		"$cmd_migrate"
	fi
}
