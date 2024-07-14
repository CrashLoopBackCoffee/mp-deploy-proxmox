"""A Python Pulumi program"""

import pathlib
import pulumi
import pulumi_command

from pve.base import RemoteConfigFiles
from pve.python import Python

config = pulumi.Config()

connection = pulumi_command.remote.ConnectionArgs(
    host=config.require('host'),
    user=config.require('ssh-user'),
    private_key=config.require_secret('ssh-private-key'),
)

if version := config.get('python-version'):
    python = Python(
        f'python-{version}',
        connection=connection,
        version=version,
    )
    pulumi.export('python-interpreter', python.interpreter_name)

RemoteConfigFiles(
    'grub',
    asset_folder=pathlib.Path('assets', 'grub'),
    connection=connection,
)

RemoteConfigFiles(
    'smtp-strato',
    asset_folder=pathlib.Path('assets', 'smtp'),
    asset_config=config.require_object('smtp'),
    connection=connection,
)
