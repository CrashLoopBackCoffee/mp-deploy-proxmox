"""A Python Pulumi program"""

import pulumi
import pulumi_command

config = pulumi.Config()

connection = pulumi_command.remote.ConnectionArgs(
    host=config.require('host'),
    user=config.require('ssh-user'),
    private_key=config.require_secret('ssh-private-key'),
)

ls = pulumi_command.remote.Command('ls', connection=connection, create='ls -la')

pulumi.export('ls stdout', ls.stdout)
pulumi.export('ls stderr', ls.stderr)
