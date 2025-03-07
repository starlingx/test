from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.ptp.system_host_if_ptp_keywords import SystemHostIfPTPKeywords
from keywords.cloud_platform.system.ptp.system_host_ptp_instance_keywords import SystemHostPTPInstanceKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_keywords import SystemPTPInstanceKeywords
from keywords.cloud_platform.system.ptp.system_ptp_instance_parameter_keywords import SystemPTPInstanceParameterKeywords
from keywords.cloud_platform.system.ptp.system_ptp_interface_keywords import SystemPTPInterfaceKeywords


class PTPTeardownExecutorKeywords(BaseKeyword):
    """
    Delete all PTP configurations using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the PTPTeardownExecutorKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """

    def delete_all_ptp_configurations(self):
        """
        Delete all PTP configurations
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)

        hostnames = SystemHostListKeywords(ssh_connection).get_system_host_list().get_controllers()
        for hostname in hostnames:
            self.remove_all_interfaces_by_hostname(hostname.get_host_name())
            self.remove_all_ptp_instances_by_hostname(hostname.get_host_name())

        self.delete_all_ptp_interface_parameters()

        self.delete_all_ptp_interfaces()

        self.delete_all_ptp_instance_parameters()

        self.delete_all_ptp_instances()

        system_ptp_instance_output = system_ptp_instance_keywords.get_system_ptp_instance_list()
        validate_equals(len(system_ptp_instance_output.get_ptp_instance_list()), 0, "Failed to clean up all PTP configurations")

    def remove_all_interfaces_by_hostname(self, hostname: str):
        """
        Remove all PTP interfaces on the specified host

        Args:
            hostname: Hostname or id
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        system_host_if_ptp_keywords = SystemHostIfPTPKeywords(ssh_connection)
        system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)

        system_ptp_interface_list_output = system_ptp_interface_keywords.get_system_ptp_interface_list()

        for ptp_inteface_obj in system_ptp_interface_list_output.get_ptp_interface_list():

            ptp_interface = ptp_inteface_obj.get_name()
            system_ptp_interface_output = system_ptp_interface_keywords.get_system_ptp_interface_show(ptp_interface)
            interface_names_on_host = system_ptp_interface_output.get_interface_names_on_host(hostname)

            for interface in interface_names_on_host :
                system_host_if_ptp_keywords.system_host_if_ptp_remove(hostname, interface, ptp_interface)

    def remove_all_ptp_instances_by_hostname(self, hostname: str):
        """
        Remove all host association

        Args:
            hostname : hostname or id
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        system_host_ptp_instance_keywords = SystemHostPTPInstanceKeywords(ssh_connection)

        system_host_ptp_instance_output = system_host_ptp_instance_keywords.get_system_host_ptp_instance_list(hostname)

        for host_ptp_instance_name_obj in system_host_ptp_instance_output.get_host_ptp_instance():
            system_host_ptp_instance_keywords.system_host_ptp_instance_remove(hostname, host_ptp_instance_name_obj.get_name())

    def delete_all_ptp_interface_parameters(self):
        """
        Delete all ptp interface level parameters
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)

        system_ptp_interface_output = system_ptp_interface_keywords.get_system_ptp_interface_list()
        for ptp_interface_obj in system_ptp_interface_output.get_ptp_interface_list():
            parameters = system_ptp_interface_output.get_ptp_interface_parameters(ptp_interface_obj)
            if parameters :
                system_ptp_interface_keywords.system_ptp_interface_parameter_delete(ptp_interface_obj.get_name(), parameters)

    def delete_all_ptp_interfaces(self):
        """
        Delete all ptp interfaces
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        system_ptp_interface_keywords = SystemPTPInterfaceKeywords(ssh_connection)
        system_ptp_interface_output = system_ptp_interface_keywords.get_system_ptp_interface_list().get_ptp_interface_list()
        for ptp_interface_obj in system_ptp_interface_output:
            system_ptp_interface_keywords.system_ptp_interface_delete(ptp_interface_obj.get_name())

    def delete_all_ptp_instance_parameters(self):
        """
        Delete all parameter to instance
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        system_ptp_instance_parameter_keywords = SystemPTPInstanceParameterKeywords(ssh_connection)

        system_ptp_instance_list_output = SystemPTPInstanceKeywords(ssh_connection).get_system_ptp_instance_list()

        for get_ptp_instance_obj in system_ptp_instance_list_output.get_ptp_instance_list():
            system_ptp_instance_show_output = SystemPTPInstanceKeywords(ssh_connection).get_system_ptp_instance_show(get_ptp_instance_obj.get_name())
            parameters = system_ptp_instance_show_output.get_ptp_instance_parameters()
            if parameters :
                system_ptp_instance_parameter_keywords.system_ptp_instance_parameter_delete(get_ptp_instance_obj.get_name(), parameters)

    def delete_all_ptp_instances(self):
        """
        Delete all ptp instances
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_active_controller_ssh()
        system_ptp_instance_keywords = SystemPTPInstanceKeywords(ssh_connection)

        system_ptp_instance_list_output = system_ptp_instance_keywords.get_system_ptp_instance_list()
        for get_ptp_instance_obj in system_ptp_instance_list_output.get_ptp_instance_list():
            system_ptp_instance_keywords.system_ptp_instance_delete(get_ptp_instance_obj.get_name())
