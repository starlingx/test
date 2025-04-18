from multiprocessing import get_logger

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ptp.ptp4l.objects.ptp4l_status_output import PTP4LStatusOutput
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from starlingx.framework.validation.validation import validate_equals


class SystemCTLStatusKeywords(BaseKeyword):
    """
    Keywords for systemctl status <service_name> cmds
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_status(self, service_name: str) -> list[str]:
        """
        Gets the status of the given service name
        Args:
            service_name (str): the service name

        Returns: the output as a list of strings - this should be consumed by a parser for the given output type

        """
        output = self.ssh_connection.send(f'systemctl status {service_name}')
        self.validate_success_return_code(self.ssh_connection)
        return output

    def verify_status_on_hostname(self, hostname :str, name : str, service_name : str) -> None:
        """
        verify systemctl ptp service status on hostname

        Args:
            hostname (str): The name of the host
            name (str): name of instance (e.g., "phc1")
            service_name (str): service name (e.g., "phc2sys@phc1.service")

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)
        
        output = SystemCTLStatusKeywords(ssh_connection).get_status(service_name)
        ptp_service_status_output = PTP4LStatusOutput(output)

        expected_service_status = "active (running)"
        observed_service_status = ptp_service_status_output.get_ptp4l_object(name).get_active()
        
        if  expected_service_status in observed_service_status :
            get_logger().log_info(f"Validation Successful - systemctl status {service_name}")
        else:
            get_logger().log_info(f"Validation Failed - systemctl status {service_name}")
            get_logger().log_info(f"Expected service status: {expected_service_status}")
            get_logger().log_info(f"Observed service status: {observed_service_status}")
            raise Exception("Validation Failed")
        

    def verify_ptp_status_and_instance_parameters_on_hostname(self, hostname :str, name : str, service_name : str, instance_parameters : str) -> None:
        """
        verify systemctl ptp service status and instance parameters on hostname

        Args:
            hostname (str): The name of the host
            name (str) : name of instance (e.g., "phc1")
            service_name (str): service name (e.g., "phc2sys@phc1.service")
            instance_parameters (str) : instance parameters 

        Returns: None

        Raises:
            Exception: raised when validate fails
        """
        lab_connect_keywords = LabConnectionKeywords()
        ssh_connection = lab_connect_keywords.get_ssh_for_hostname(hostname)
        
        
        output = SystemCTLStatusKeywords(ssh_connection).get_status(service_name)
        ptp_service_status_output = PTP4LStatusOutput(output)

        expected_service_status = "active (running)"
        observed_service_status = ptp_service_status_output.get_ptp4l_object(name).get_active()
        get_command = ptp_service_status_output.get_ptp4l_object(name).get_command()
        
        # From the input string "cmdline_opts='-s enpXXs0f2 -O -37 -m'"
        # The extracted output string is '-s enpXXs0f2 -O -37 -m'
        instance_parameter = eval(instance_parameters.split("=")[1])
        
        if  expected_service_status in observed_service_status and instance_parameter in get_command :
            get_logger().log_info(f"Validation Successful - systemctl status {service_name}")
        else:
            get_logger().log_info(f"Validation Failed - systemctl status {service_name}")
            get_logger().log_info(f"Expected service status: {expected_service_status}")
            get_logger().log_info(f"Observed service status: {observed_service_status}")
            get_logger().log_info(f"Expected instance parameter: {instance_parameter}")
            get_logger().log_info(f"Observed instance parameter: {get_command}")
            raise Exception("Validation Failed")

