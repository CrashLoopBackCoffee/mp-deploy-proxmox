"""Pulumi resources to update GRUB bootloader options."""

import pulumi
import pulumi_command


class Grub(pulumi.ComponentResource):
    def __init__(
        self,
        name: str,
        connection: pulumi.Input[pulumi_command.remote.ConnectionArgs],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        module_path = self.__module__.replace('.', ':')
        super().__init__(
            f'{module_path}:{self.__class__.__name__}',
            name,
            props={},
            opts=opts,
        )

        grub_config_files = pulumi.FileArchive('assets/grub/')
        grub_config_files_copies = pulumi_command.remote.CopyToRemote(
            'grub-config-files',
            connection=connection,
            source=grub_config_files,
            remote_path='/etc/default/grub.d/',
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_command.remote.Command(
            'grub-update',
            connection=connection,
            create='update-grub',
            opts=pulumi.ResourceOptions(depends_on=[grub_config_files_copies], parent=self),
        )

        self.register_outputs({})
