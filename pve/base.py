"""Shared utilities."""

import pulumi


class BaseComponent(pulumi.ComponentResource):
    @property
    def resource_type(self):
        """Derive resource type name from Python module and class name.

        Should be use in derived class __init__ implementations.
        """
        return f'{self.__module__.replace('.', ':')}:{self.__class__.__name__}'
