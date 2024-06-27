"""A Python Pulumi program"""

import pulumi
import pulumi_command

config = pulumi.Config()

connection = pulumi_command.remote.ConnectionArgs(
    host=config.require('host'),
    user=config.require('ssh-user'),
    private_key=config.require_secret('ssh-private-key'),
)

build_system = pulumi_command.remote.Command(
    'python build system',
    connection=connection,
    create='sudo apt update -y && sudo apt install -y build-essential libssl-dev zlib1g-dev libbz2-dev '
    'libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils '
    'tk-dev libffi-dev liblzma-dev python3-openssl git',
)

pulumi.export('build_system stdout', build_system.stdout)
pulumi.export('build_system stderr', build_system.stderr)

# TODO: build a component to install Python3.12 on PVE following:
#  https://wiki.crowncloud.net/?How_to_Install_Python_3_12_on_Debian_12
