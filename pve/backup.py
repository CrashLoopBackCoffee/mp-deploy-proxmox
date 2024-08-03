"""Backup configuration."""
import pathlib
import typing as t
from pve.util import BaseComponent, RemoteConfigFiles

import pulumi
import pulumi_command


class Backup(BaseComponent):
    """Configures Proxmox backups."""

    def __init__(
        self,
        name: str,
        *,
        asset_folder: pathlib.Path,
        config: dict[str, t.Any],
        temp_folder: pathlib.Path,
        connection: pulumi.Input[pulumi_command.remote.ConnectionArgs],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__(
            self.resource_type,
            name,
            props={},
            opts=opts,
        )

        fs = config['filesystem']
        mount = config['mountpoint']
        fstab_line = f'{fs} {mount} ext4 defaults 0'
        refresh_mounts = 'systemctl daemon-reload && mount -a'

        backup_dir = pulumi_command.remote.Command(
            f'{name}-mount',
            connection=connection,
            add_previous_output_in_env=False,
            create=f'mkdir {mount} && echo {fstab_line} >> /etc/fstab && {refresh_mounts}',
            delete=f"sed -i '/{fs.replace('/', r'\/')}/d' /etc/fstab && umount {fs} && {refresh_mounts} && rmdir {mount}",
            opts=pulumi.ResourceOptions(
                parent=self,
                delete_before_replace=True,
                replace_on_changes=['*'],
            ),
        )

        storage_name = config['storage']
        storage = pulumi_command.remote.Command(
            f'{name}-storage',
            connection=connection,
            add_previous_output_in_env=False,
            create=f'pvesm add dir {storage_name} --path={mount} --content=backup --prune-backups=keep-all=1 --shared=0',
            delete=f'pvesm remove {storage_name}',
            opts=pulumi.ResourceOptions(
                parent=self,
                delete_before_replace=True,
                replace_on_changes=['*'],
                depends_on=[backup_dir],
            ),
        )

        RemoteConfigFiles(
            f'{name}-jobs',
            asset_folder=asset_folder,
            asset_config=config,
            temp_folder=temp_folder,
            connection=connection,
            opts=pulumi.ResourceOptions(
                parent=self,
                delete_before_replace=True,
                replace_on_changes=['*'],
                depends_on=[storage],
            ),
        )

        self.register_outputs({})
