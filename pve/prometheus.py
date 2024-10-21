"""Prometheus monitoring setup for Proxmox node and guests.

Assumes a running Prometheus instance in the Proxmox cluster that has access to the target PVE node.
Installing a Prometheus LXC is a one-liner. See https://tteck.github.io/Proxmox/#prometheus-lxc for
more information.

See https://community.hetzner.com/tutorials/proxmox-prometheus-metrics for the core logic
implemented in this module.
"""

import pathlib
import pulumi
import pulumi_command
from pve.util import BaseComponent, RemoteConfigFiles
import typing as t


class PrometheusNode(BaseComponent):
    """Configures Prometheus-based monitoring for one PVE node.

    - Installs the pve-exporter on the target PVE node.
    - Configures the (pre-exisiting) cluster-local Prometheus to scrape the exporter and remote_write to another
      Prometheus (e.g. part of Grafana cloud).
    """

    def __init__(
        self,
        name: str,
        *,
        config: dict[str, t.Any],
        asset_folder: pathlib.Path,
        connection: pulumi.Input[pulumi_command.remote.ConnectionArgs],
        opts: pulumi.ResourceOptions | None = None,
    ) -> None:
        super().__init__(
            self.resource_type,
            name,
            props={},
            opts=opts,
        )

        non_idempotent_command_args: dict[str, t.Any] = {
            'connection': connection,
            'add_previous_output_in_env': False,
            'opts': pulumi.ResourceOptions(
                parent=self,
                delete_before_replace=True,
                replace_on_changes=['*'],
            ),
        }

        exporter_config = config['exporter']

        exporter_username = exporter_config['username']
        exporter_password = exporter_config['password']
        pulumi_command.remote.Command(
            f'{name}-exporter-user',
            create=pulumi.Output.concat(
                f'pveum user add {exporter_username}@pve --password "',
                exporter_password,
                '" --comment "Prometheus exporter service account." && ',
                f'pveum acl modify / -user {exporter_username}@pve -role PVEAuditor && ',
                f'useradd -s /bin/false {exporter_username}',
            ),
            delete=f'userdel {exporter_username} && pveum user delete {exporter_username}@pve',
            **non_idempotent_command_args,
        )

        venv_path = '/opt/prometheus-pve-exporter'
        pulumi_command.remote.Command(
            f'{name}-exporter',
            create=f'apt update -y && apt install -y python3-venv && '
            f'python3 -m venv {venv_path} && {venv_path}/bin/pip install prometheus-pve-exporter',
            delete=f'rm -rf {venv_path}',
            **non_idempotent_command_args,
        )

        pve_exporter = RemoteConfigFiles(
            f'{name}-exporter-config',
            asset_folder=asset_folder / 'exporter',
            asset_config=exporter_config,
            post_run=f'chown -v root:{exporter_username} /etc/prometheus/pve.yml && '
            'chmod -v 640 /etc/prometheus/pve.yml && '
            'systemctl daemon-reload && '
            'systemctl enable prometheus-pve-exporter.service && '
            'systemctl start prometheus-pve-exporter.service',
            connection=connection,
            opts=pulumi.ResourceOptions(
                parent=self,
                replace_on_changes=['*'],
            ),
        )

        vmid = exporter_config['vmid']
        RemoteConfigFiles(
            f'{name}-config',
            asset_folder=asset_folder / 'local',
            asset_config=config['local'],
            post_run=f'pct push {vmid} /tmp/prometheus.yml /etc/prometheus/prometheus.yml && '
            f'rm -f /tmp/prometheus.yml && '
            f'pct exec {vmid} systemctl restart prometheus',
            connection=connection,
            opts=pulumi.ResourceOptions(
                parent=self,
                replace_on_changes=['*'],
                depends_on=pve_exporter,
            ),
        )
