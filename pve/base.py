"""Shared utilities."""

import datetime
import pathlib
import typing as t
import pulumi
import pulumi_command


class BaseComponent(pulumi.ComponentResource):
    @property
    def resource_type(self):
        """Derive resource type name from Python module and class name.

        Should be use in derived class __init__ implementations.
        """
        return f'{self.__module__.replace('.', ':')}:{self.__class__.__name__}'


class RemoteConfigFiles(BaseComponent):
    """Copies files to remote after string formatting them with passed config dict."""

    def __init__(
        self,
        name: str,
        *,
        asset_folder: pathlib.Path,
        asset_config: dict[str, t.Any] | None = None,
        connection: pulumi.Input[pulumi_command.remote.ConnectionArgs],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__(
            self.resource_type,
            name,
            props={},
            opts=opts,
        )

        if asset_config:
            extended_config = asset_config | {'name': name}
            tmpdir_path = pathlib.Path('.generated', name)
            tmpdir_path.mkdir(parents=True, exist_ok=True)
        else:
            extended_config = None
            tmpdir_path = None

        remote_files: list[pulumi.Resource] = []

        for index, path in enumerate(asset_folder.rglob('*.cfg')):
            if asset_config:
                assert extended_config and tmpdir_path, 'set in if clause above'

                format_string = path.read_text()
                local_path = tmpdir_path / f'file-{index}'
                local_path.write_text(format_string.format(**extended_config))
            else:
                local_path = path

            remote_path = pathlib.Path('/', path.relative_to(asset_folder)).as_posix()

            pulumi.log.info(remote_path)

            remote_files.append(
                pulumi_command.remote.CopyToRemote(
                    remote_path,
                    connection=connection,
                    source=pulumi.asset.FileAsset(local_path),
                    remote_path=remote_path,
                    opts=pulumi.ResourceOptions(parent=self),
                )
            )

        if asset_config:
            assert tmpdir_path, 'set in if clause above'

            pulumi_command.local.Command(
                'cleanup-templates',
                create=f'rm -rf {tmpdir_path.as_posix()}',
                opts=pulumi.ResourceOptions(parent=self, depends_on=remote_files),
                # run always:
                triggers=[datetime.datetime.now().timestamp()],
            )

        # TODO: register generated file paths as outputs
        self.register_outputs({})
