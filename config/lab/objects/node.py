from typing import Any, List, Optional


class Node:
    """
    Class to handle lab nodes
    """

    def __init__(
        self,
        name: str,
        node: dict[str, Any],
        lab_config: dict[str, Any] = {},
    ):
        self.name: str = name
        self.node_type: str = node["node_type"]
        self.node_capabilities: List[str] = node["node_capabilities"]

        self.ip: str = node["ip"]
        self.ssh_port: int = int(node.get("ssh_port", lab_config.get("ssh_port", 22)))

        self.bm_ip: Optional[str] = node.get("bm_ip")
        self.bm_port: int = int(node.get("bm_port", 443))

        self.bm_username: Optional[str] = node.get("bm_username")
        self.bm_password: str = node.get("bm_password", lab_config.get("bm_password", ""))

        # Values below are on the host object but not written to the config
        self.subfunctions = []

    def get_name(self) -> str:
        """Getter for name.

        Returns:
            str: The node name.
        """
        return self.name

    def get_ip(self) -> str:
        """Getter for ip.

        Returns:
            str: The ip for the node.
        """
        return self.ip

    def get_ssh_port(self) -> int:
        """Getter for ssh_port.

        Returns:
            int: The ssh_port for the node.
        """
        return self.ssh_port

    def get_type(self) -> str:
        """Getter for type.

        Returns:
            str: The lab type.
        """
        return self.node_type

    def get_node_capabilities(self) -> List[str]:
        """Gets the node capabilities.

        Returns:
            List[str]: The node capabilities.
        """
        return self.node_capabilities

    def set_node_capabilities(self, capabilities: List[str]):
        """Setter for node capabilities -- replaces the list.

        Args:
            capabilities (List[str]): The capabilities to set.
        """
        self.node_capabilities = capabilities

    def append_node_capability(self, capability: str):
        """Appends the node capability.

        Args:
            capability (str): The capability to append.
        """
        if capability not in self.node_capabilities:
            self.node_capabilities.append(capability)

    def set_subfunctions(self, subfunctions: List[str]):
        """Setter for sub functions.

        Args:
            subfunctions (List[str]): The subfunctions.
        """
        self.subfunctions = subfunctions

    def get_subfunctions(self) -> List[str]:
        """Getter for subfunctions.

        Returns:
            List[str]: The subfunctions.
        """
        return self.subfunctions

    def set_bm_ip(self, bm_ip: str):
        """Setter for bm_ip.

        Args:
            bm_ip (str): The bm ip.
        """
        self.bm_ip = bm_ip

    def get_bm_ip(self) -> Optional[str]:
        """Getter for bm ip.

        Returns:
            Optional[str]: The bm ip.
        """
        return self.bm_ip

    def set_bm_port(self, bm_port: int):
        """Setter for bm_port.

        Args:
            bm_port (int): The bm port.
        """
        self.bm_port = bm_port

    def get_bm_port(self) -> int:
        """Getter for bm port."""
        return self.bm_port

    def set_bm_username(self, bm_username: str):
        """Setter for bm username.

        Args:
            bm_username (str): The bm username.
        """
        self.bm_username = bm_username

    def get_bm_username(self) -> Optional[str]:
        """Getter for bm username.

        Returns:
            Optional[str]: The bm username.
        """
        return self.bm_username

    def set_bm_password(self, bm_password: str):
        """Setter for bm password.

        Args:
            bm_password (str): The bm password.
        """
        self.bm_password = bm_password

    def get_bm_password(self) -> str:
        """Getter for bm password.

        Returns:
            str: The bm password.
        """
        return self.bm_password

    def to_log_strings(self) -> List[str]:
        """Returns a list of strings that can be logged to show all the node configs.

        Returns:
            List[str]: A list of strings to be sent to the logger.
        """
        log_strings = []
        log_strings.append(f"Node name: {self.get_name()}")
        log_strings.append(f"     type: {self.get_type()}")
        log_strings.append(f"     ip: {self.get_ip()}")
        log_strings.append(f"     port: {self.get_ssh_port()}")
        return log_strings
