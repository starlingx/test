from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class SystemCTLShowKeywords(BaseKeyword):
    """Keywords for 'systemctl show' commands.

    Provides methods to query systemd unit properties.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to target host.
        """
        self.ssh_connection = ssh_connection

    def get_property(self, unit_name: str, property_name: str) -> str:
        """Get a single property value from a systemd unit.

        Runs: systemctl show <unit_name> --property=<property_name>

        Args:
            unit_name (str): The systemd unit name (e.g., 'k8sinfra.slice').
            property_name (str): The property to query (e.g., 'CPUWeight').

        Returns:
            str: The property value (portion after '=').
        """
        output = self.ssh_connection.send(
            f"systemctl show {unit_name} --property={property_name}"
        )
        result = output.strip() if isinstance(output, str) else output[0].strip()
        # Output format is "PropertyName=value"
        if "=" in result:
            return result.split("=", 1)[1]
        return result

    def get_properties(self, unit_name: str, properties: list) -> dict:
        """Get multiple property values from a systemd unit.

        Args:
            unit_name (str): The systemd unit name.
            properties (list): List of property names to query.

        Returns:
            dict: Dictionary of property_name -> value.
        """
        props_arg = ",".join(properties)
        output = self.ssh_connection.send(
            f"systemctl show {unit_name} --property={props_arg}"
        )
        lines = output if isinstance(output, list) else output.strip().split("\n")
        result = {}
        for line in lines:
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                result[key] = value
        return result
