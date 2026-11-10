"""Explicit input for one policy traffic scenario."""


class IPsecPolicyTrafficInput:
    """Configure a single owned TCP/UDP scenario."""

    def __init__(self, image: str, client_node: str, server_node: str, protocol: str = "tcp", port: int = 18080, family: int = 4, same_node: bool = False):
        """Capture the requested traffic topology and protocol.

        Args:
            image (str): Immutable Python-capable image.
            client_node (str): Eligible client node.
            server_node (str): Eligible server node.
            protocol (str): tcp or udp.
            port (int): Destination service/target port.
            family (int): IP family, 4 or 6.
            same_node (bool): Explicit same-node control.
        """
        self.image = image
        self.client_node = client_node
        self.server_node = server_node
        self.protocol = protocol
        self.port = port
        self.family = family
        self.same_node = same_node

    def get_image(self) -> str:
        """Return configured image.

        Returns:
            str: Configured scenario value.
        """
        return self.image

    def get_client_node(self) -> str:
        """Return configured client node.

        Returns:
            str: Configured scenario value.
        """
        return self.client_node

    def get_server_node(self) -> str:
        """Return configured server node.

        Returns:
            str: Configured scenario value.
        """
        return self.server_node

    def get_protocol(self) -> str:
        """Return configured protocol.

        Returns:
            str: Configured scenario value.
        """
        return self.protocol

    def get_port(self) -> int:
        """Return configured port.

        Returns:
            int: Configured scenario value.
        """
        return self.port

    def get_family(self) -> int:
        """Return configured family.

        Returns:
            int: Configured scenario value.
        """
        return self.family

    def get_same_node(self) -> bool:
        """Return configured same node.

        Returns:
            bool: Configured scenario value.
        """
        return self.same_node
