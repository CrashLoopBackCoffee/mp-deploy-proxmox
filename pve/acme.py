"""Configuration of ACME-based TLS certificates."""

import typing as t

import pulumi
import pulumi_command
from pve.util import BaseComponent


class AcmeDirectoryNotFoundError(Exception):
    pass


class Acme(BaseComponent):
    """Configures ACME-based certificate exchange."""

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

        get_directories = pulumi_command.remote.Command(
            f'{name}-directories',
            connection=connection,
            add_previous_output_in_env=False,
            create='pvesh get /cluster/acme/directories --output-format=json',
            opts=pulumi.ResourceOptions(parent=self),
        )

        def directory_url(directories_: list[dict[str, str]]) -> str:
            """Return the ACME directory URL, depending on staging config."""
            for dir_ in directories_:
                if ('staging' in dir_['name'].lower()) is config['staging']:
                    return dir_['url']

            raise AcmeDirectoryNotFoundError()

        acme_directory_url = pulumi.Output.json_loads(get_directories.stdout).apply(directory_url)

        get_terms = pulumi_command.remote.Command(
            f'{name}-terms',
            connection=connection,
            add_previous_output_in_env=False,
            create='pvesh get /cluster/acme/tos --output-format=json',
            opts=pulumi.ResourceOptions(parent=self),
        )

        acme_terms_url = pulumi.Output.json_loads(get_terms.stdout).apply(lambda t: t)

        account_config = config['account']
        acme_account = pulumi_command.remote.Command(
            f'{name}-account',
            connection=connection,
            add_previous_output_in_env=False,
            create=pulumi.Output.concat(
                'pvesh create /cluster/acme/account',
                ' --name=',
                account_config['name'],
                ' --contact=',
                account_config['contact'],
                ' --directory=',
                acme_directory_url,
                ' --tos_url=',
                acme_terms_url,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        plugin_config = config['plugin']
        plugin_data = pulumi.Output.all(*plugin_config['data']).apply(
            lambda entries: '\n'.join(f'{e["key"]}={e["value"]}' for e in entries)
        )
        plugin_data_filename = '.acme-plugin-data'
        acme_plugin = pulumi_command.remote.Command(
            f'{name}-plugin',
            connection=connection,
            add_previous_output_in_env=False,
            create=pulumi.Output.concat(
                'echo -e "',
                plugin_data,
                '">',
                plugin_data_filename,
                ' && ',
                'pvenode acme plugin add dns ',
                plugin_config['name'],
                ' --api=',
                plugin_config['api'],
                ' --data=',
                plugin_data_filename,
                ' && ',
                'rm -f ',
                plugin_data_filename,
            ),
            opts=pulumi.ResourceOptions(parent=self),
        )

        pulumi_command.remote.Command(
            f'{name}-domain-cert-order',
            connection=connection,
            add_previous_output_in_env=False,
            create=f'pvenode config set --acmedomain0 domain={config['domain']},plugin={plugin_config['name']} && '
            f'pvenode config set --acme=account={account_config['name']} && '
            f'pvenode acme cert order --force=1',
            opts=pulumi.ResourceOptions(depends_on=[acme_account, acme_plugin], parent=self),
        )

        self.register_outputs({})
