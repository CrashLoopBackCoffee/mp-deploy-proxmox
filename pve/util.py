"""Shared utilities."""

import hashlib
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
        post_run: str | None = None,
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

        remote_files: list[pulumi_command.remote.CopyToRemote] = []

        for path in asset_folder.rglob('*.cfg'):
            if asset_config:
                assert extended_config and temp_folder, 'set in if clause above'

                sha256 = hashlib.sha256()
                sha256.update(path.as_posix().encode())
                path_hash = sha256.hexdigest()

                format_string = path.read_text()
                local_path = temp_folder / f'file-{path_hash}'
                local_path.write_text(format_string.format(**extended_config))
            else:
                local_path = path

            remote_path = pathlib.Path('/', path.relative_to(asset_folder)).as_posix()
            remote_files.append(
                pulumi_command.remote.CopyToRemote(
                    remote_path,
                    connection=connection,
                    source=pulumi.asset.FileAsset(local_path),
                    remote_path=remote_path,
                    opts=pulumi.ResourceOptions(parent=self),
                )
            )

        if post_run:
            pulumi_command.remote.Command(
                f'{name}-post-run',
                connection=connection,
                create=post_run,
                opts=pulumi.ResourceOptions(depends_on=remote_files, parent=self),
            )

        self.register_outputs({'files': [rf.remote_path for rf in remote_files]})
