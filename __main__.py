"""A Python Pulumi program"""

import pathlib
import tempfile
import pulumi
import pulumi_command

from pve.acme import Acme
from pve.backup import Backup
from pve.prometheus import PrometheusNode
from pve.util import RemoteConfigFiles
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

asset_dir = pathlib.Path('assets')
temp_dir = tempfile.TemporaryDirectory(prefix='pulumi-')
temp_path = pathlib.Path(temp_dir.name)

RemoteConfigFiles(
    'grub',
    asset_folder=asset_dir / 'grub',
    post_run='update-grub',
    connection=connection,
)

RemoteConfigFiles(
    'smtp-strato',
    asset_folder=asset_dir / 'smtp',
    asset_config=config.require_object('smtp'),
    temp_folder=temp_path,
    connection=connection,
)

Acme('acme', config=config.require_object('acme'), connection=connection)

Backup(
    'backup',
    config=config.require_object('backup'),
    asset_folder=asset_dir / 'backup',
    temp_folder=temp_path,
    connection=connection,
)

PrometheusNode(
    'prometheus',
    config=config.require_object('prometheus'),
    asset_folder=asset_dir / 'prometheus',
    temp_folder=temp_path,
    connection=connection,
)
