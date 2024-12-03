from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_object import SystemHostObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostOutput:
    """
    Class for System Host Output
    """

    def __init__(self, system_host_output):
        self.system_hosts: [SystemHostObject] = []
        system_table_parser = SystemTableParser(system_host_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_host_object = SystemHostObject(
                    int(value['id']),
                    value['hostname'],
                    value['personality'],
                    value['administrative'],
                    value['operational'],
                    value['availability'],
                )
                if 'capabilities' in value:
                    system_host_object.set_capabilities(value['capabilities'])
                if 'uptime' in value:
                    system_host_object.set_uptime(int(value['uptime']))
                if 'subfunctions' in value:
                    system_host_object.set_sub_functions(value['subfunctions'].split(','))
                if 'bm_ip' in value:
                    system_host_object.set_bm_ip(value['bm_ip'])
                if 'bm_username' in value:
                    system_host_object.set_bm_username(value['bm_username'])
                self.system_hosts.append(system_host_object)

            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_hosts(self) -> [SystemHostObject]:
        """
        Returns the list of system host objects
        Returns:

        """
        return self.system_hosts

    def get_host(self, host_name: str) -> SystemHostObject:
        """
        Returns the host with the given name
        Args:
            host_name (): the name of the host

        Returns:

        """
        hosts = list(filter(lambda host: host.get_host_name() == host_name, self.system_hosts))
        if len(hosts) == 0:
            raise KeywordException(f"No host with name {host_name} was found.")

        return hosts[0]

    def get_standby_controller(self) -> SystemHostObject:
        """
        Gets the standby controller
        Returns: the standby controller

        """
        hosts = list(
            filter(
                lambda host: host.get_capabilities().get_personality() == 'Controller-Standby',
                self.system_hosts,
            )
        )
        if len(hosts) == 0:
            raise KeywordException("No Standby controller was found")

        return hosts[0]

    def get_active_controller(self) -> SystemHostObject:
        """
        Gets the active controller
        Returns: the active controller

        """
        hosts = list(
            filter(
                lambda host: host.get_capabilities().get_personality() == 'Controller-Active',
                self.system_hosts,
            )
        )
        if len(hosts) == 0:
            raise KeywordException("No Active controller was found")

        return hosts[0]

    def get_controllers(self) -> list[SystemHostObject]:
        """
        Gets the list of controllers
        Returns (list[SystemHostObject]): the list of controllers

        """
        hosts = list(
            filter(
                lambda host: 'controller' in host.get_personality(),
                self.system_hosts,
            )
        )
        if len(hosts) == 0:
            raise KeywordException("No controller was found.")

        return hosts

    def get_computes(self) -> [SystemHostObject]:
        """
        Gets the compute
        Returns: the compute

        """
        hosts = list(
            filter(
                lambda host: host.get_personality() == 'worker',
                self.system_hosts,
            )
        )
        if len(hosts) == 0:
            raise KeywordException("No computes were found")

        return hosts

    def get_storages(self) -> [SystemHostObject]:
        """
        Gets the storages
        Returns: the storages

        """
        hosts = list(
            filter(
                lambda host: host.get_personality() == 'storage',
                self.system_hosts,
            )
        )
        if len(hosts) == 0:
            raise KeywordException("No storage nodes were found")

        return hosts

    @staticmethod
    def is_valid_output(value):
        """
        Checks to ensure the output has the correct keys
        Args:
            value (): the value to check

        Returns:

        """
        valid = True
        if 'id' not in value:
            get_logger().log_error(f'id is not in the output value: {value}')
            valid = False
        if 'hostname' not in value:
            get_logger().log_error(f'host_name is not in the output value: {value}')
            valid = False
        if 'personality' not in value:
            get_logger().log_error(f'personality is not in the output value: {value}')
            valid = False
        if 'administrative' not in value:
            get_logger().log_error(f'adminstrative is not in the output value: {value}')
            valid = False
        if 'operational' not in value:
            get_logger().log_error(f'operational is not in the output value: {value}')
            valid = False
        if 'availability' not in value:
            get_logger().log_error(f'id is not in the output value: {value}')
            valid = False

        return valid
