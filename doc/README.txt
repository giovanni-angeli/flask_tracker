
export PROJECT_ROOT="/opt/PROJECTS/flask_tracker"
export DEPLOY_ROOT="/opt/flask_tracker"
eralchemy -i sqlite:///${DEPLOY_ROOT}/data/tracker.v7.sqlite -o ${PROJECT_ROOT}/doc/tracker.v7.sqlite.dot
vi  ${PROJECT_ROOT}/doc/tracker.v7.sqlite.dot
dot ${PROJECT_ROOT}/doc/tracker.v7.sqlite.dot -Tsvg  -o ${PROJECT_ROOT}/doc/tracker.v7.sqlite.svg
