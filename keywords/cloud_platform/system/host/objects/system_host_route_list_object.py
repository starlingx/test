class SystemHostRouteListObject:
    """
    Class to hold attributes of a system route list as returned by system host route list command
    """

    def __init__(
        self,
        uuid: str,
        if_name: str,
        network: str,
        prefix: int,
        gateway: str,
        metric: int,
    ):
        self.uuid = uuid
        self.if_name = if_name
        self.network = network
        self.prefix = prefix
        self.gateway = gateway
        self.metric = metric

    def get_uuid(self) -> str:
        """
        Getter for uuid

        Returns: the uuid

        """
        return self.uuid

    def get_ifname(self) -> str:
        """

        Getter for interface name

        Returns: interface name

        """
        return self.if_name

    def get_network(self) -> str:
        """
        Getter for network address

        Returns: the network address

        """
        return self.network

    def get_prefix(self) -> int:
        """
        Getter for route prefix

        Returns: the route prefix

        """
        return self.prefix

    def get_gateway(self) -> str:
        """
        Getter for the route gateway

        Returns: the gateway address

        """
        return self.gateway

    def get_metric(self) -> int:
        """
        Getter for route metric

        Returns: metric value

        """
        return self.metric
