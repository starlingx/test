import re

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.linux.ip.object.ip_br_addr_output import IPBrAddrOutput
from keywords.linux.ip.object.ip_link_show_output import IPLinkShowOutput


class IPKeywords(BaseKeyword):
    """
    Keywords for linux ip command
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def ip_link_show_interface(self, interface_name) -> IPLinkShowOutput:
        """
        IP link show command for the given interface name
        Args:
            interface_name (): the interface name

        Returns:

        """
        output = self.ssh_connection.send(f'ip link show {interface_name}')
        self.validate_success_return_code(self.ssh_connection)
        ip_link_show_output = IPLinkShowOutput(output)

        return ip_link_show_output

    def get_ip_address_from_pod(self, pod_name: str, interface_name: str) -> str:
        """
        Gets the ipaddress from the given interface in the pod
        Args:
            pod_name (): the name of the pod
            interface_name (): the interface name

        Returns:

        """

        lab_config = ConfigurationManager.get_lab_config()

        ip_designation = ''
        if lab_config.is_ipv6():
            ip_designation = '-6'

        exec_in_pod = KubectlExecInPodsKeywords(self.ssh_connection)
        output = exec_in_pod.run_pod_exec_cmd(pod_name, f'ip {ip_designation} addr list')

        # output is a list, need to put as a string and remove return characters
        output_str = ' '.join(output).replace('\n', '')

        # Given the below output form, find the global ip for the interface given. i.e. for interface net1 we want
        # the ip address: 2626:1::8e22:765f:6121:eb59
        #
        # 1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 state UNKNOWN qlen 1000
        # inet6 ::1/128 scope host         valid_lft forever preferred_lft forever 2:
        # eth0@if73: <BROADCAST,MULTICAST,UP,LOWER_UP,M-DOWN> mtu 1500 state UP qlen 1000
        # inet6 2626:1::8e22:765f:6121:eb42/128 scope global
        # valid_lft forever preferred_lft forever
        # inet6 fe80::d814:88ff:fe27:f6f5/64 scope link
        # valid_lft forever preferred_lft forever 41:
        # net1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 state UP qlen 1000
        # inet6 2626:1::8e22:765f:6121:eb59/122 scope global
        # valid_lft forever preferred_lft forever
        # inet6 fe80::e057:9cff:fe60:f650/64 scope link
        # valid_lft forever preferred_lft forever

        reg_exp = f"{interface_name}: .*inet.* (\S+).*\/.*global"
        match = re.search(fr"{reg_exp}", output_str)

        if match:
            ip = match.group(1)
        else:
            raise KeywordException(f'unable to find the ip address for pod {pod_name} and interface {interface_name}')
        return ip

    def add_route_in_pod(self, pod_name: str, interface_name: str):
        """
        Adds the route in the pod for the given interface
        Args:
            pod_name (): the name of the pod
            interface_name (): the interface name

        Returns:

        """
        lab_config = ConfigurationManager.get_lab_config()

        if lab_config.is_ipv6():
            route = '2626:1::/64'  # this is currently a hardcoded value we should use in all test cases
        else:
            route = '192.168.1.0/24'  # this is currently a hardcoded value we should use in all test cases

        exec_in_pod = KubectlExecInPodsKeywords(self.ssh_connection)
        exec_in_pod.run_pod_exec_cmd(pod_name, f'ip route add {route} dev {interface_name}')

    def get_ip_br_addr(self) -> IPBrAddrOutput:
        """
        Executes the 'ip -br addr' command to list all physical and virtual network interfaces on this 'ssh_connection'.

        Args: None.

        Returns:
            IPBrAddrOutput: an instance of IPBrAddrOutput, which provides a convenient way to represent the output of
            the 'ip -br addr' command.

        """
        output = self.ssh_connection.send('ip -br addr')
        self.validate_success_return_code(self.ssh_connection)
        ip_br_addr_output = IPBrAddrOutput(output)

        return ip_br_addr_output

    def set_ip_port_state(self, port: str, state: str = 'up'):
        """
        sets a ip specific port state UP or DOWN as specified via ip link cmd

        Args:
            port : port to set
            state: state to set port (up or down)

        Returns:
        """
        self.ssh_connection.send_as_sudo(f"ip link set dev {port} {state}")
        self.validate_success_return_code(self.ssh_connection)
