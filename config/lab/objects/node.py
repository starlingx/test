from typing import List


class Node:
    """
    Class to handle lab nodes
    """

    def __init__(self, name: str, node: []):
        self.name = name
        self.ip = node['ip']
        self.node_type = node['node_type']
        self.node_capabilities: [str] = node['node_capabilities']
        self.bm_ip = None
        self.bm_username = None
        self.bm_ip = None
        if 'bm_ip' in node:
            self.bm_ip = node['bm_ip']
        self.bm_username = None
        if 'bm_username' in node:
            self.bm_username = node['bm_username']

        # Values below are on the host object but not written to the config
        self.subfunctions = []

    def get_name(self) -> str:
        """
        Getter for name
        Returns: the node name

        """
        return self.name

    def get_ip(self) -> str:
        """
        Getter for ip
        Returns: the ip for the node

        """
        return self.ip

    def get_type(self) -> str:
        """
        Getter for type
        Returns: the lab type

        """
        return self.node_type

    def get_node_capabilities(self) -> [str]:
        """
        Gets the node capabilities
        Returns: the node capabilities

        """
        return self.node_capabilities

    def set_node_capabilities(self, capabilities: [str]):
        """
        Setter for node capabilities -- replaces the list
        Args:
            capabilities (): the capability to append

        Returns:

        """
        self.node_capabilities = capabilities

    def append_node_capability(self, capability: str):
        """
        Appends the node capability
        Args:
            capability ():

        Returns:

        """
        if capability not in self.node_capabilities:
            self.node_capabilities.append(capability)

    def set_subfunctions(self, subfunctions: [str]):
        """
        Setter for sub functions
        Args:
            subfunctions (): the subfunctions

        Returns:

        """
        self.subfunctions = subfunctions

    def get_subfunctions(self) -> [str]:
        """
        Getter for subfunctions
        Returns:

        """
        return self.subfunctions

    def set_bm_ip(self, bm_ip: str):
        """
        Setter for bm_ip
        Args:
            bm_ip (): the bm ip

        Returns:

        """
        self.bm_ip = bm_ip

    def get_bm_ip(self) -> str:
        """
        Getter for bm ip
        Returns:

        """
        return self.bm_ip

    def set_bm_username(self, bm_username: str):
        """
        Setter for bm username
        Args:
            bm_username (): the bm username

        Returns:

        """
        self.bm_username = bm_username

    def get_bm_username(self) -> str:
        """
        Getter for bm username
        Returns:

        """
        return self.bm_username

    def to_log_strings(self) -> List[str]:
        """
        This function will return a list of strings that can be logged to show all the node configs.
        Returns: A List of strings to be sent to the logger.

        """
        log_strings = []
        log_strings.append(f"Node name: {self.get_name()}")
        log_strings.append(f"     ip: {self.get_ip()}")
        log_strings.append(f"     type: {self.get_type()}")

        return log_strings
