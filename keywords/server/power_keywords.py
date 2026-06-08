from typing import Optional, Type

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.server.power_keywords_implementation import PowerKeywordsImplementation


class PowerKeywords(BaseKeyword):
    """Public interface for generic power keywords.

    The actual logic lives in :class:`PowerKeywordsImplementation` (or a
    subclass of it). This class is the stable entry point that callers
    use; it forwards each public method to the active implementation.

    External users can swap in a custom implementation by
    calling :meth:`set_implementation_class` with a subclass of
    :class:`PowerKeywordsImplementation`.
    """

    implementation_class: Type[PowerKeywordsImplementation] = PowerKeywordsImplementation

    @classmethod
    def set_implementation_class(cls, implementation_class: Optional[Type[PowerKeywordsImplementation]]) -> None:
        """Register the implementation class to use for power keywords.

        Args:
            implementation_class (Optional[Type[PowerKeywordsImplementation]]):
                A subclass of :class:`PowerKeywordsImplementation` to use
                for new :class:`PowerKeywords` instances, or ``None`` to
                fall back to the StarlingX default.

        Raises:
            TypeError: If ``implementation_class`` is not ``None`` and is
                not a subclass of :class:`PowerKeywordsImplementation`.
        """
        if implementation_class is None:
            PowerKeywords.implementation_class = PowerKeywordsImplementation
            return

        if not (isinstance(implementation_class, type) and issubclass(implementation_class, PowerKeywordsImplementation)):
            raise TypeError("implementation_class must be a subclass of PowerKeywordsImplementation")

        PowerKeywords.implementation_class = implementation_class

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection passed to the
                underlying implementation.
        """
        self.ssh_connection = ssh_connection
        self.implementation = PowerKeywords.implementation_class(ssh_connection)

    def get_implementation(self) -> PowerKeywordsImplementation:
        """Return the implementation instance backing this keyword object.

        Returns:
            PowerKeywordsImplementation: The implementation instance
            constructed for this :class:`PowerKeywords`.
        """
        return self.implementation

    def power_on(self, host_name: str) -> bool:
        """Power on the given host and wait for it to be in a good state.

        Args:
            host_name (str): The name of the host.

        Returns:
            bool: True if the host powers on successfully.

        Raises:
            KeywordException: If the host fails to power on within the
                expected time.
        """
        return self.implementation.power_on(host_name)

    def is_powered_on(self, host_name: str, power_on_wait_timeout: int = 1800) -> bool:
        """Check that the host is powered on and in a good state.

        Args:
            host_name (str): The name of the host.
            power_on_wait_timeout (int): The time to wait for the host to
                be powered on, in seconds.

        Returns:
            bool: True if the host is powered on, healthy and has no
            failure alarms; False otherwise.
        """
        return self.implementation.is_powered_on(host_name, power_on_wait_timeout)

    def power_off(self, host_name: str) -> bool:
        """Power off the host.

        Args:
            host_name (str): The name of the host.

        Returns:
            bool: True if the host is powered off successfully.

        Raises:
            KeywordException: If the host fails to power off within the
                expected time.
        """
        return self.implementation.power_off(host_name)

    def is_powered_off(self, host_name: str) -> bool:
        """Wait for the host to be powered off.

        Args:
            host_name (str): The name of the host.

        Returns:
            bool: True if the host is powered off and host operations
            are disabled; False otherwise.
        """
        return self.implementation.is_powered_off(host_name)

    def power_cycle(self, host_name: str) -> None:
        """Power cycle the host.

        Args:
            host_name (str): The name of the host.
        """
        self.implementation.power_cycle(host_name)
