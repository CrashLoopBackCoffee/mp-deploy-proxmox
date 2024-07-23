"""Shared utilities."""

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
        temp_folder: pathlib.Path | None = None,
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
        else:
            extended_config = None

        remote_files: list[str] = []

        for index, path in enumerate(asset_folder.rglob('*.cfg')):
            if asset_config:
                assert extended_config and temp_folder, 'set in if clause above'

                format_string = path.read_text()
                local_path = temp_folder / f'file-{index}'
                local_path.write_text(format_string.format(**extended_config))
            else:
                local_path = path

            remote_path = pathlib.Path('/', path.relative_to(asset_folder)).as_posix()

            pulumi.log.info(remote_path)

            pulumi_command.remote.CopyToRemote(
                remote_path,
                connection=connection,
                source=pulumi.asset.FileAsset(local_path),
                remote_path=remote_path,
                opts=pulumi.ResourceOptions(parent=self),
            )
            remote_files.append(remote_path)

        self.register_outputs({'files': remote_files})
