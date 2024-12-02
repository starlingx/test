from typing import List

import json5
from config.host.objects.host_configuration import HostConfiguration
from config.lab.objects.credentials import Credentials
from config.lab.objects.node import Node
from framework.resources.resource_finder import get_stx_resource_path


class LabConfig:
    """
    Class to hold lab config
    """

    def __init__(self, config):

        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the lab config file: {config}")
            raise

        lab_dict = json5.load(json_data)
        self.floating_ip = lab_dict['floating_ip']
        self.lab_name = lab_dict['lab_name']
        self.lab_type = lab_dict['lab_type']
        self.admin_credentials = Credentials(lab_dict['admin_credentials'])
        self.bm_password = lab_dict['bm_password']
        self.use_jump_server = lab_dict['use_jump_server']
        if 'jump_server_config' in lab_dict:
            jump_host_config_location = get_stx_resource_path(lab_dict['jump_server_config'])
            self.jump_server_config = HostConfiguration(jump_host_config_location)

        self.ssh_port: int = 22
        if 'ssh_port' in lab_dict:
            self.ssh_port = int(lab_dict['ssh_port'])

        self.lab_capabilities = []
        if 'lab_capabilities' in lab_dict:
            self.lab_capabilities = lab_dict['lab_capabilities']

        if 'horizon_url' in lab_dict:
            self.horizon_url = lab_dict['horizon_url']
        else:
            self.horizon_url = f"https://[{self.floating_ip}]:8443/"

        if 'horizon_credentials' in lab_dict:
            self.horizon_credentials = Credentials(lab_dict['horizon_credentials'])
        else:
            self.horizon_credentials = Credentials({"user_name": "admin", "password": self.admin_credentials.get_password()})

        if 'rest_credentials' in lab_dict:
            self.rest_credentials = Credentials(lab_dict['rest_credentials'])
        else:
            self.rest_credentials = Credentials({"user_name": "admin", "password": self.admin_credentials.get_password()})

        self.nodes = []
        self.subclouds: [LabConfig] = []

        # if subclouds are listed in the config get the list with the subcloud's names.
        if 'subclouds' in lab_dict:
            for subcloud in lab_dict['subclouds']:
                subcloud_config_location = get_stx_resource_path((lab_dict['subclouds'][subcloud]))
                self.subclouds.append(LabConfig(subcloud_config_location))

        if 'nodes' in lab_dict:
            for node in lab_dict['nodes']:
                self.nodes.append(Node(node, lab_dict['nodes'][node]))

        self.ipv6 = True
        if ':' not in self.floating_ip:
            self.ipv6 = False

        self.is_dc_lab = len(self.subclouds) > 0
        # If there is a value in the config, override the above value
        if 'is_dc' in lab_dict:
            self.is_dc_lab = lab_dict['is_dc']

        self.system_controller_ip = None  # only gets set if DC system and only in the subcloud
        if 'system_controller_ip' in lab_dict:
            self.system_controller_ip = lab_dict['system_controller_ip']

        self.system_controller_name = None  # only gets set if DC system and only in the subcloud
        if 'system_controller_name' in lab_dict:
            self.system_controller_name = lab_dict['system_controller_name']

        self.lab_config_file = config

    def get_floating_ip(self) -> str:
        """
        Getter for floating ip
        Returns: the floating ip

        """
        return self.floating_ip

    def set_floating_ip(self, floating_ip: str):
        """
        Setter for floating ip
        Args:
            floating_ip (str): the host's floating ip

        Returns:

        """
        self.floating_ip = floating_ip

        # Update ipv4 vs ipv6 value.
        self.ipv6 = True
        if ':' not in self.floating_ip:
            self.ipv6 = False

    def get_lab_name(self) -> str:
        """
        Getter for lab name
        Returns: the lab name

        """
        return self.lab_name

    def set_lab_name(self, lab_name: str):
        """
        Setter for lab name
        Args:
            lab_name (str): the lab name

        Returns:

        """
        self.lab_name = lab_name

    def get_lab_type(self) -> str:
        """
        Getter for lab type
        Returns: the lab type

        """
        return self.lab_type

    def set_lab_type(self, lab_type: str):
        """
        Setter for lab type
        Args:
            lab_type (): the lab type

        Returns:

        """
        self.lab_type = lab_type

    def get_admin_credentials(self) -> Credentials:
        """
        Getter for admin credentials
        Returns: the admin credentials

        """
        return self.admin_credentials

    def get_horizon_credentials(self) -> Credentials:
        """
        Getter for Horizon credentials
        Returns: the Horizon credentials

        """
        return self.horizon_credentials

    def get_rest_credentials(self) -> Credentials:
        """
        Getter for Rest credentials
        Returns: the Rest credentials

        """
        return self.rest_credentials

    def set_nodes(self, nodes: [Node]):
        """
        Sets the labs nodes (clear any nodes already created)
        Args:
            nodes (): the nodes

        Returns:

        """
        self.nodes = nodes

    def get_nodes(self) -> [Node]:
        """
        Getter for lab nodes
        Returns: the lab nodes

        """
        return self.nodes

    def get_node(self, lab_node_name) -> Node:
        """
        Returns the lab node with the given name
        Args:
            lab_node_name (): the name of the lab node ex. Controller-0

        Returns: the lab node

        """
        for node in self.nodes:
            if node.name == lab_node_name:
                return node
        return None

    def is_ipv6(self):
        """
        Return True is lab is ipv6, False otherwise
        Returns:

        """
        return self.ipv6

    def get_subclouds(self) -> []:
        """
        Getter for subclouds
        Returns: the list of subclouds

        """
        return self.subclouds

    def set_subclouds(self, subclouds: []):
        """
        Setter for subclouds
        Args:
            subclouds (list): the list of subclouds.

        Returns:

        """
        self.subclouds = subclouds

    def get_subcloud(self, subcloud_name):
        """
        Getter for subcloud
        Args:
            subcloud_name (): the subcloud name

        Returns: the subcloud

        """
        for subcloud in self.subclouds:
            if subcloud.get_lab_name() == subcloud_name:
                return subcloud
        return None

    def get_subcloud_names(self) -> [str]:
        """
        Getter for the names of the subclouds in the list of subclouds in LabConfig file.
        Args: None

        Returns: a list of the subcloud names from the list of subclouds in the LabConfig file.

        """
        return [subcloud.get_lab_name() for subcloud in self.subclouds]

    def get_horizon_url(self):
        """
        Getter for Horizon URL

        Returns: The URL to connect to Horizon

        """
        return self.horizon_url

    def set_horizon_url(self, url):
        """
        Setter for horizon url
        Args:
            url (): the horizon url

        Returns:

        """
        self.horizon_url = url

    def is_dc(self) -> bool:
        """
        Getter for is dc
        Returns: true if it's a dc, false otherwise

        """
        return self.is_dc_lab

    def is_use_jump_server(self) -> bool:
        """
        Getter for use jump server
        Returns:

        """
        return self.use_jump_server

    def get_jump_host_configuration(self) -> HostConfiguration:
        """
        Getter for jump host configuration
        Returns:

        """
        return self.jump_server_config

    def get_ssh_port(self) -> int:
        """
        Getter for the SSH port.
        Returns:

        """
        return self.ssh_port

    def get_lab_capabilities(self) -> [str]:
        """
        Getter for lab capabilities
        Returns:

        """
        return self.lab_capabilities

    def add_lab_capability(self, capability: str):
        """
        Setter for lab capability
        Args:
            capability ():

        Returns:

        """
        if capability not in self.lab_capabilities:
            self.lab_capabilities.append(capability)

    def get_lab_config_file(self) -> str:
        """
        Getter for lab config file
        Returns:

        """
        return self.lab_config_file

    def set_lab_config_file(self, lab_config_file: str):
        """
        Setter for lab config file
        Args:
            lab_config_file (str): the lab config file path.

        Returns:

        """
        self.lab_config_file = lab_config_file

    def get_bm_password(self) -> str:
        """
        Getter for bm password
        Returns:

        """
        return self.bm_password

    def get_system_controller_ip(self) -> str:
        """
        Getter for system_controller_ip
        Returns: the system_controller_ip

        """
        return self.system_controller_ip

    def set_system_controller_ip(self, system_controller_ip: str):
        """
        Setter for system_controller_ip
        Args:
            system_controller_ip (): the system_controller_ip

        Returns:

        """
        self.system_controller_ip = system_controller_ip

    def get_system_controller_name(self) -> str:
        """
        Getter for system_controller_name
        Returns: system_controller_name

        """
        return self.system_controller_name

    def set_system_controller_name(self, system_controller_name: str):
        """
        Setter for system_controller_name
        Args:
            system_controller_name (): the system_controller_name

        Returns:

        """
        self.system_controller_name = system_controller_name

    def to_log_strings(self) -> List[str]:
        """
        This function will return a list of strings that can be logged to show all the lab configs.
        Returns: A List of strings to be sent to the logger.

        """
        log_strings = []
        log_strings.append(f"lab_name: {self.get_lab_name()}")
        log_strings.append(f"lab_type: {self.get_lab_type()}")
        log_strings.append(f"floating_ip: {self.get_floating_ip()}")
        log_strings.append(f"is_ipv6: {self.is_ipv6()}")
        log_strings.append(f"ssh_port: {self.get_ssh_port()}")
        log_strings.append(f"admin_credentials: {self.get_admin_credentials().to_string()}")
        log_strings.append(f"horizon_url: {self.get_horizon_url()}")
        log_strings.append(f"horizon_credentials: {self.get_horizon_credentials().to_string()}")
        log_strings.append(f"is_dc: {self.is_dc()}")
        log_strings.append(f"use_jump_server: {self.is_use_jump_server()}")
        if self.use_jump_server:
            for log_string in self.get_jump_host_configuration().to_log_strings():
                log_strings.append(f"    {log_string}")
        for node in self.get_nodes():
            for log_string in node.to_log_strings():
                log_strings.append(log_string)
        for subcloud in self.get_subclouds():
            log_strings.append("Subcloud")
            for log_string in subcloud.to_log_strings():
                log_strings.append(f"    {log_string}")

        return log_strings
