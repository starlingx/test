class SystemAddrpoolListObject:
    """
    Class to handle the data provided by the 'system addrpool-list' command execution. This command generates the
    output table shown below, where each object of this class represents a single row in that table.

    +--------------------------------------+-----------------------------+----------+--------+--------+---------------------------+------------------+---------------------+---------------------+-----------------+
    | uuid                                 | name                        | network  | prefix | order  | ranges                    | floating_address | controller0_address | controller1_address | gateway_address |
    +--------------------------------------+-----------------------------+----------+--------+--------+---------------------------+------------------+---------------------+---------------------+-----------------+
    | 8091e435-996a-4543-bce3-00b283a22075 | cluster-host-subnet-ipv6    | aefd:205 | 64     | random | ['aefd:205::1-aefd:205::  | aefd:205::1      | aefd:205::2         | aefd:205::3         | None            |
    |                                      |                             | ::       |        |        | ffff:ffff:ffff:fffe']     |                  |                     |                     |                 |
    |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
    | b5a65ed0-7370-49cf-b089-ba19b23c47e1 | cluster-pod-subnet-ipv6     | aefd:206 | 64     | random | ['aefd:206::1-aefd:206::  | None             | None                | None                | None            |
    |                                      |                             | ::       |        |        | ffff:ffff:ffff:fffe']     |                  |                     |                     |                 |
    |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
    | 696f3f8f-7e3b-4974-990c-99ae904bc808 | cluster-service-subnet-ipv6 | aefd:207 | 112    | random | ['aefd:207::1-aefd:207::  | None             | None                | None                | None            |
    |                                      |                             | ::       |        |        | fffe']                    |                  |                     |                     |                 |
    |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
    | 6f437a9f-105e-4e3d-956d-5c0a5eaa0b30 | management-ipv6             | fdff:10: | 64     | random | ['fdff:10:80:237::2-fdff: | fdff:10:80:237:: | fdff:10:80:237::3   | fdff:10:80:237::4   | None            |
    |                                      |                             | 80:237:: |        |        | 10:80:237::ffff']         | 2                |                     |                     |                 |
    |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
    | 27a769b0-105f-41f2-a389-c49012b10233 | multicast-subnet-ipv6       | ff05::80 | 112    | random | ['ff05::80:237:0:1-ff05:: | None             | None                | None                | None            |
    |                                      |                             | :237:0:0 |        |        | 80:237:0:fffe']           |                  |                     |                     |                 |
    |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
    | 7e82fd4c-d3bb-4766-817d-32d4cd69729c | oam-ipv6                    | 2620:10a | 64     | random | ['2620:10a:a001:aa0c::    | 2620:10a:a001:   | None                | None                | 2620:10a:a001:  |
    |                                      |                             | :a001:   |        |        | 1-2620:10a:a001:aa0c:ffff | aa0c::216        |                     |                     | aa0c::1         |
    |                                      |                             | aa0c::   |        |        | :ffff:ffff:fffe']         |                  |                     |                     |                 |
    |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
    | 82a770b0-15da-4d96-ad87-1b5639f3aec2 | pxeboot                     | 192.168. | 24     | random | ['192.168.202.1-192.168.  | 192.168.202.1    | 192.168.202.2       | 192.168.202.3       | None            |
    |                                      |                             | 202.0    |        |        | 202.254']                 |                  |                     |                     |                 |
    |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
    +--------------------------------------+-----------------------------+----------+--------+--------+---------------------------+------------------+---------------------+---------------------+-----------------+
    
    """

    def __init__(
        self,
        uuid,
        name,
        network,
        order,
        ranges,
        floating_address,
        controller0_address,
        controller1_address,
        gateway_address
        ):
        self.uuid = uuid
        self.name = name
        self.network = network
        self.order = order
        self.ranges = ranges
        self.floating_address = floating_address
        self.controller0_address = controller0_address
        self.controller1_address = controller1_address
        self.gateway_address = gateway_address

    def get_uuid(self) -> str:
        """
        Getter for uuid
        Returns: the uuid
        """
        return self.uuid
    
    def get_name(self) -> str:
        """
        Getter for name
        Returns: the name
        """
        return self.name

    def get_network(self) -> str:
        """
        Getter for network
        Returns: the network
        """
        return self.network

    def get_order(self) -> str:
        """
        Getter for order
        Returns: the order
        """
        return self.order
    
    def get_ranges(self) -> str:
        """
        Getter for ranges
        Returns: the ranges
        """
        return self.ranges

    def get_floating_address(self) -> str:
        """
        Getter for floating_address
        Returns: the floating_address
        """
        return self.floating_address

    def get_controller0_address(self) -> str:
        """
        Getter for controller0_address
        Returns: the controller0_address
        """
        return self.controller0_address

    def get_controller1_address(self) -> str:
        """
        Getter for controller1_address
        Returns: the controller1_address
        """
        return self.controller1_address
    
    def get_gateway_address(self) -> str:
        """
        Getter for gateway_address
        Returns: the gateway_address
        """
        return self.gateway_address
