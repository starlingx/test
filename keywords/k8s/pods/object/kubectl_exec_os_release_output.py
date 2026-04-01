from typing import Union

from keywords.k8s.pods.object.kubectl_exec_os_release_object import KubectlExecOSReleaseObject


class KubectlExecOSReleaseOutput:
    """A class to interact with and retrieve information from /etc/os-release output from a pod.

    This class provides methods to parse and access OS release information
    from the cat /etc/os-release command output executed inside a pod.
    """

    def __init__(self, kubectl_exec_os_release_output: Union[str, list[str]]):
        """Constructor.

        Args:
            kubectl_exec_os_release_output (Union[str, list[str]]): Raw output from running cat /etc/os-release in a pod.
        """
        self.os_release_object = KubectlExecOSReleaseObject()
        self._parse(kubectl_exec_os_release_output)

    def _parse(self, output: Union[str, list[str]]) -> None:
        """Parse the raw os-release output into a structured object.

        Args:
            output (Union[str, list[str]]): Raw output from cat /etc/os-release.
        """
        lines = output.strip().split('\n') if isinstance(output, str) else output
        for line in lines:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                if key == 'NAME':
                    self.os_release_object.set_name(value)
                elif key == 'VERSION':
                    self.os_release_object.set_version(value)
                elif key == 'ID':
                    self.os_release_object.set_id(value)
                elif key == 'VERSION_ID':
                    self.os_release_object.set_version_id(value)
                elif key == 'PRETTY_NAME':
                    self.os_release_object.set_pretty_name(value)

    def get_os_release_object(self) -> KubectlExecOSReleaseObject:
        """Get the parsed OS release object.

        Returns:
            KubectlExecOSReleaseObject: Parsed OS release information.
        """
        return self.os_release_object

    def get_version(self) -> str:
        """Get OS version.

        Returns:
            str: OS version.
        """
        return self.os_release_object.get_version()

    def get_name(self) -> str:
        """Get OS name.

        Returns:
            str: OS name.
        """
        return self.os_release_object.get_name()

    def get_version_id(self) -> str:
        """Get OS version ID.

        Returns:
            str: OS version ID.
        """
        return self.os_release_object.get_version_id()

    def get_pretty_name(self) -> str:
        """Get pretty formatted name.

        Returns:
            str: Pretty formatted name.
        """
        return self.os_release_object.get_pretty_name()
