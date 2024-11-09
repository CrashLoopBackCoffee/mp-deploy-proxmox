"""A Python Pulumi program"""

import pathlib
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
    connection=connection,
)

Acme('acme', config=config.require_object('acme'), connection=connection)

Backup(
    'backup',
    config=config.require_object('backup'),
    asset_folder=asset_dir / 'backup',
    connection=connection,
)

cloud_prometheus_config = config.require_object('grafana-cloud')['prometheus']
prometheus_config = config.require_object('prometheus')
prometheus_config['local'] |= {
    'remote-url': cloud_prometheus_config['push-url'],
    'remote-username': cloud_prometheus_config['username'],
    'remote-password': cloud_prometheus_config['password'],
}

PrometheusNode(
    'prometheus',
    config=prometheus_config,
    asset_folder=asset_dir / 'prometheus',
    connection=connection,
)

# provide access credentials to access node from other stacks:
pulumi.export('host', connection.host)
pulumi.export('ssh-user', connection.user)
pulumi.export('ssh-private-key', connection.private_key)
