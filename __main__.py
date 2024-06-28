"""A Python Pulumi program"""

import pulumi
import pulumi_command

import pve
import pve.python

config = pulumi.Config()

connection = pulumi_command.remote.ConnectionArgs(
    host=config.require('host'),
    user=config.require('ssh-user'),
    private_key=config.require_secret('ssh-private-key'),
)

version = config.require('python-version')
python = pve.python.Python(
    f'python-{version}',
    connection=connection,
    version=version,
)

pulumi.export('python-interpreter', python.interpreter_name)
