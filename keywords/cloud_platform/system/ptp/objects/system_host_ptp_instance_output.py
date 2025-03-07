from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.ptp.objects.system_host_ptp_instance_object import SystemHostPTPInstanceObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostPTPInstanceOutput:
    """
    This class parses the output of host-ptp-instance command into an object of type SystemHostPTPInstanceObject.
    """

    def __init__(self, system_host_ptp_instance_output):
        """
        Constructor

        Args:
        system_host_ptp_instance_output (str): Output of the system host-ptp-instance command.
        """
        self.system_host_ptp_instance_output: list[SystemHostPTPInstanceObject] = []
        system_table_parser = SystemTableParser(system_host_ptp_instance_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            system_host_ptp_instance_object = SystemHostPTPInstanceObject()
            if "uuid" in value:
                system_host_ptp_instance_object.set_uuid(value["uuid"])

            if "name" in value:
                system_host_ptp_instance_object.set_name(value["name"])

            if "service" in value:
                system_host_ptp_instance_object.set_service(value["service"])
            self.system_host_ptp_instance_output.append(system_host_ptp_instance_object)

    def get_host_ptp_instance(self) -> list[SystemHostPTPInstanceObject]:
        """
        Returns the parsed system host-ptp-instance object

        Returns:
            list[SystemHostPTPInstanceObject] : list representation of system host-ptp-instance object
        """
        return self.system_host_ptp_instance_output

    def get_host_ptp_instance_for_name(self, name: str) -> SystemHostPTPInstanceObject:
        """
        Returns the parsed system host-ptp-instance object for name

        Args:
            name: name or UUID for ptp instance

        Returns:
            SystemHostPTPInstanceObject : system host-ptp-instance object
        """
        host_ptp_instance = list(filter(lambda item: item.get_name() == name, self.system_host_ptp_instance_output))
        if len(host_ptp_instance) == 0:
            raise KeywordException(f"No ptp instance was found for {name}")

        return host_ptp_instance[0]
