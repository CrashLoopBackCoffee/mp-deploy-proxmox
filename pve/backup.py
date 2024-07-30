"""Backup configuration."""
import typing as t
from pve.util import BaseComponent

import pulumi
import pulumi_command


class Backup(BaseComponent):
    """Configures Proxmox backups."""

    def __init__(
        self,
        name: str,
        *,
        config: dict[str, t.Any],
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
            mount,
            connection=connection,
            add_previous_output_in_env=False,
            create=f'mkdir {mount} && echo {fstab_line} >> /etc/fstab && {refresh_mounts}',
            delete=f'sed -i {fs.replace('/', r'\/')} /etc/fstab && umount {fs} && {refresh_mounts}',
            opts=pulumi.ResourceOptions(
                parent=self,
                delete_before_replace=True,
                replace_on_changes=['*'],
            ),
        )

        self.register_outputs({})
