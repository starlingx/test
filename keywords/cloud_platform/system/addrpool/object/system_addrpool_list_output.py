from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.addrpool.object.system_addrpool_list_object import SystemAddrpoolListObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemAddrpoolListOutput:
    """
    This class parses the output of the command 'system addrpool-list'
    The parsing result is a 'SystemAddrpoolListObject' instance.

    Example:
        'system addrpool-list'
        +--------------------------------------+-----------------------------+----------+--------+--------+---------------------------+------------------+---------------------+---------------------+-----------------+
        | uuid                                 | name                        | network  | prefix | order  | ranges                    | floating_address | controller0_address | controller1_address | gateway_address |
        +--------------------------------------+-----------------------------+----------+--------+--------+---------------------------+------------------+---------------------+---------------------+-----------------+
        | 1e836335-80a0-427c-ae18-87dbe5f0e20e | cluster-host-subnet-ipv4    | 192.168. | 24     | random | ['192.168.206.1-192.168.  | 192.168.206.1    | 192.168.206.2       | 192.168.206.3       | None            |
        |                                      |                             | 206.0    |        |        | 206.254']                 |                  |                     |                     |                 |
        |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
        | 88062da8-7839-4a99-b051-e24ef6c8bf75 | cluster-pod-subnet-ipv4     | 172.16.0 | 16     | random | ['172.16.0.1-172.16.255.  | None             | None                | None                | None            |
        |                                      |                             | .0       |        |        | 254']                     |                  |                     |                     |                 |
        |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
        | 1d00691b-f01e-46e9-9e54-916d766d1277 | cluster-service-subnet-ipv4 | 10.96.0. | 12     | random | ['10.96.0.1-10.111.255.   | None             | None                | None                | None            |
        |                                      |                             | 0        |        |        | 254']                     |                  |                     |                     |                 |
        |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
        | 38d18176-481e-4ef2-9540-25e448b34dc0 | management-ipv4             | 10.8.69. | 24     | random | ['10.8.69.2-10.8.69.254'] | 10.8.69.2        | 10.8.69.3           | 10.8.69.4           | None            |
        |                                      |                             | 0        |        |        |                           |                  |                     |                     |                 |
        |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
        | ccf0d793-0ed0-4d6e-a407-7186cf391955 | multicast-subnet-ipv4       | 239.1.1. | 28     | random | ['239.1.1.1-239.1.1.14']  | None             | None                | None                | None            |
        |                                      |                             | 0        |        |        |                           |                  |                     |                     |                 |
        |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
        | c3f4f28e-aa84-47ec-843e-2e1efcff563e | oam-ipv4                    | 128.224. | 23     | random | ['128.224.48.1-128.224.49 | 128.224.48.232   | None                | None                | 128.224.48.1    |
        |                                      |                             | 48.0     |        |        | .254']                    |                  |                     |                     |                 |
        |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
        | b46bc265-e5e5-4980-b476-35599ebe5961 | pxeboot                     | 192.168. | 24     | random | ['192.168.202.1-192.168.  | 192.168.202.1    | 192.168.202.2       | 192.168.202.3       | None            |
        |                                      |                             | 202.0    |        |        | 202.254']                 |                  |                     |                     |                 |
        |                                      |                             |          |        |        |                           |                  |                     |                     |                 |
        +--------------------------------------+-----------------------------+----------+--------+--------+---------------------------+------------------+---------------------+---------------------+-----------------+

    """


    def __init__(self, system_addrpool_list_output):
        """
        Constructor
        Args:
            system_addrpool_list_output: the output of the command 'system addrpool-list'
        """
        self.system_addrpool: [SystemAddrpoolListObject] = []
        system_table_parser = SystemTableParser(system_addrpool_list_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                self.system_addrpool.append(
                    SystemAddrpoolListObject(
                        value['uuid'],
                        value['name'],
                        value['network'],
                        value['order'],
                        value['ranges'],
                        value['floating_address'],
                        value['controller0_address'],
                        value['controller1_address'],
                        value['gateway_address'],
                    )
                )
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_addrpool(self) -> [SystemAddrpoolListObject]:
        """
        Returns the list of addrpool objects
        """
        return self.system_addrpool

    def get_floating_address_by_name(self, name: str) -> str:
        """
        Gets the floating address for the given name.
        Args:
            name: the name of the desired addrpool

        Returns:
            The floating address of the addrpool with the specified name.
        """
        addrpools = list(filter(lambda pool: name in pool.get_name(), self.system_addrpool))
        if not addrpools:
            raise KeywordException(f"No addrpool with name {name} was found.")
        return addrpools[0].get_floating_address()

    @staticmethod
    def is_valid_output(value):
        required_keys = ['uuid', 'name', 'network', 'order', 'ranges', 'floating_address', 'controller0_address', 'controller1_address', 'gateway_address']
        for key in required_keys:
            if key not in value:
                get_logger().log_error(f'{key} is not in the output value: {value}')
                return False
        return True








