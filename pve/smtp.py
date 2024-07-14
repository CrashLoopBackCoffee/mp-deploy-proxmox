"""Pulumi resources to update SMTP configuration."""

import datetime
import pathlib
import typing as t

import pulumi
import pulumi_command

from pve.base import BaseComponent


class Smtp(BaseComponent):
    def __init__(
        self,
        name: str,
        smtp_config: dict[str, t.Any],
        connection: pulumi.Input[pulumi_command.remote.ConnectionArgs],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__(
            self.resource_type,
            name,
            props={},
            opts=opts,
        )

        asset_folder = pathlib.Path('assets', 'smtp')
        extended_smtp_config = smtp_config | {'name': name}

        tmpdir_path = pathlib.Path('.generated', 'smtp-gen')
        tmpdir_path.mkdir(parents=True, exist_ok=True)

        remote_files: list[pulumi.Resource] = []

        for index, path in enumerate(asset_folder.rglob('*.cfg')):
            format_string = path.read_text()

            local_path = tmpdir_path / f'generated-{index}'
            local_path.write_text(format_string.format(**extended_smtp_config))

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

        pulumi_command.local.Command(
            'cleanup-templates',
            create=f'rm -rf {tmpdir_path.as_posix()}',
            opts=pulumi.ResourceOptions(parent=self, depends_on=remote_files),
            # run always:
            triggers=[datetime.datetime.now().timestamp()],
        )

        self.register_outputs({})
