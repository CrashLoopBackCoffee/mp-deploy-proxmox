"""A Python Pulumi program"""

import pulumi
import pulumi_command

config = pulumi.Config()

connection = pulumi_command.remote.ConnectionArgs(
    host=config.require('host'),
    user=config.require('ssh-user'),
    private_key=config.require_secret('ssh-private-key'),
)

packages = (
    'build-essential',
    'libssl-dev',
    'zlib1g-dev',
    'libbz2-dev',
    'libreadline-dev',
    'libsqlite3-dev',
    'wget',
    'curl',
    'llvm',
    'libncurses5-dev',
    'libncursesw5-dev',
    'xz-utils',
    'tk-dev',
    'libffi-dev',
    'liblzma-dev',
    'python3-openssl',
    'git',
)
build_system = pulumi_command.remote.Command(
    'python build system',
    connection=connection,
    create=' && '.join(
        (
            'apt-get update -y',
            f'apt-get install --no-install-recommends -y {' '.join(packages)}',
        )
    ),
)

python_version = config.require('python-version')
python_sources = pulumi_command.remote.Command(
    'python sources',
    connection=connection,
    create=' && '.join(
        (
            f'wget https://www.python.org/ftp/python/{python_version}/Python-{python_version}.tgz',
            f'tar -xf Python-{python_version}.tgz && rm -f Python-{python_version}.tgz',
        )
    ),
    opts=pulumi.ResourceOptions(depends_on=[build_system]),
)

python_build = pulumi_command.remote.Command(
    'python build',
    connection=connection,
    create=' && '.join(
        (
            f'cd Python-{python_version}',
            './configure --enable-optimizations',
            'make -j 2'
        )
    ),
    opts=pulumi.ResourceOptions(depends_on=[python_sources]),
)

python_install = pulumi_command.remote.Command(
    'python install',
    connection=connection,
    create=' && '.join(
        (
            f'cd Python-{python_version}',
            'make altinstall'
        )
    ),
    opts=pulumi.ResourceOptions(depends_on=[python_build]),
)
