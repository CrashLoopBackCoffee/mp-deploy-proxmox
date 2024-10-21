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

    files: list[str]

    def __init__(
        self,
        name: str,
        *,
        asset_folder: pathlib.Path,
        asset_config: dict[str, t.Any] | None = None,
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

        remote_file_path_strs: list[str] = []
        generated_file_resources: list[pulumi.Resource] = []

        result_texts: list[pulumi.Output[str]] = []

        for path in asset_folder.rglob('*'):
            if not path.is_file():
                continue

            result_text = pulumi.Output.from_input(path.read_text())
            if asset_config:
                assert extended_config, 'set in if clause above'
                # config might contain secrets:
                result_text = pulumi.Output.secret(
                    pulumi.Output.format(result_text, **extended_config)
                )

            remote_file_path = pathlib.Path('/', path.relative_to(asset_folder))
            remote_file_path_str = remote_file_path.as_posix()
            remote_parent_path_str = remote_file_path.parent.as_posix()

            # CopyToRemote is not flexible enough: it computes the hash of the file to copy at
            # _registration_ time, where some templating inputs are not yet available (e.g. ESC
            # secrets or resource outputs). While we can override the hash comparison by passing
            # another trigger, CopyToRemoute seems to actually load the string also at registration
            # time, i.e. a later update has not the desired effect. So workaround this limitation be
            # running a command that prints the templated string to file:
            generated_file_resources.append(
                pulumi_command.remote.Command(
                    f'{remote_file_path_str}',
                    connection=connection,
                    create=result_text.apply(
                        lambda content,
                        parent_path=remote_parent_path_str,
                        file_path=remote_file_path_str: ';'.join(
                            (
                                f'mkdir -p {parent_path}',
                                # take advantage of Python escaping its strings for the shell:
                                f'printf {content!r} > {file_path}',
                            )
                        )
                    ),
                    opts=pulumi.ResourceOptions(parent=self),
                )
            )

            result_texts.append(result_text)
            remote_file_path_strs.append(remote_file_path_str)

        if post_run:
            pulumi_command.remote.Command(
                f'{name}-post-run',
                connection=connection,
                create=post_run,
                triggers=result_texts + remote_file_path_strs,
                opts=pulumi.ResourceOptions(parent=self, depends_on=generated_file_resources),
            )

        self.files = remote_file_path_strs
        self.register_outputs({'files': self.files})
