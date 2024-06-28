"""Pulumi resources to install an up-to-date Python interpreter."""

import pulumi
import pulumi_command


class Python(pulumi.ComponentResource):
    version = pulumi.Output[str]
    interpreter_name = pulumi.Output[str]

    build_system_packages = ' '.join(
        (
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
    )

    def __init__(
        self,
        name: str,
        connection: pulumi.Input[pulumi_command.remote.ConnectionArgs],
        version: str,
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        module_path = self.__module__.replace('.', ':')
        super().__init__(
            f'{module_path}:{self.__class__.__name__}',
            name,
            {
                'version': version,
                'interpreter_name': None,
            },
            opts,
        )

        build_system = pulumi_command.remote.Command(
            f'{name}-build-system',
            connection=connection,
            create=' && '.join(
                (
                    'apt-get update -y',
                    f'apt-get install --no-install-recommends -y {self.build_system_packages}',
                )
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        python_sources = pulumi_command.remote.Command(
            f'{name}-sources',
            connection=connection,
            create=' && '.join(
                (
                    f'wget https://www.python.org/ftp/python/{version}/Python-{version}.tgz',
                    f'tar -xf Python-{version}.tgz && rm -f Python-{version}.tgz',
                )
            ),
            opts=pulumi.ResourceOptions(depends_on=[build_system], parent=self),
        )

        python_build = pulumi_command.remote.Command(
            f'{name}-build',
            connection=connection,
            create=' && '.join(
                (
                    f'cd Python-{version}',
                    './configure --enable-optimizations',
                    'make -j 2',
                )
            ),
            opts=pulumi.ResourceOptions(depends_on=[python_sources], parent=self),
        )

        pulumi_command.remote.Command(
            f'{name}-install',
            connection=connection,
            create=' && '.join((f'cd Python-{version}', 'make altinstall')),
            opts=pulumi.ResourceOptions(depends_on=[python_build], parent=self),
        )

        major, minor, _ = version.split('.')
        self.register_outputs(
            {
                'version': version,
                'interpreter_name': f'python{major}.{minor}',
            }
        )
