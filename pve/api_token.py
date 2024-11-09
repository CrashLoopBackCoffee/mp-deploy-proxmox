"""Creation of an API token to be used with REST API or Proxmox provider."""

import pulumi
import pulumi_command


def create_api_token(
    name: str,
    *,
    username: pulumi.Input[str],
    connection: pulumi.Input[pulumi_command.remote.ConnectionArgs],
):
    token_command = pulumi_command.remote.Command(
        f'api-token-{name}',
        connection=connection,
        add_previous_output_in_env=False,
        create=f'pveum user token add {username}@pam {name} -privsep 0 --comment "Configuration by Pulumi IaC." --output-format=json',
        delete=f'pveum user token remove {username}@pam {name}',
        logging=pulumi_command.remote.Logging.NONE,
        opts=pulumi.ResourceOptions(
            delete_before_replace=True,
            replace_on_changes=['*'],
            additional_secret_outputs=['stdout'],
        ),
    )

    token_dict = pulumi.Output.json_loads(token_command.stdout)
    return token_dict.apply(lambda d: f'{d['full-tokenid']}={d['value']}')
