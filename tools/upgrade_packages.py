# coding: utf-8

"""

cosider executing in shell:

    $ pip install pip-review
    $ pip-review -h
    $ pip-review -v
    $ pip-review -a

"""


import pkg_resources
from subprocess import call

packages = [dist.project_name for dist in pkg_resources.working_set]
call("pip install --upgrade " + ' '.join(packages), shell=True)
