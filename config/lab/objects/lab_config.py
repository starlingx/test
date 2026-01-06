from typing import List, Optional

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
        self.floating_ip = lab_dict["floating_ip"]
        self.lab_name = lab_dict["lab_name"]
        self.lab_type = lab_dict["lab_type"]
        self.admin_credentials = Credentials(lab_dict["admin_credentials"])
        self.bm_password = lab_dict["bm_password"]
        self.use_jump_server = lab_dict["use_jump_server"]
        if "jump_server_config" in lab_dict:
            jump_host_config_location = get_stx_resource_path(lab_dict["jump_server_config"])
            self.jump_server_config = HostConfiguration(jump_host_config_location)

        self.ssh_port: int = 22
        if "ssh_port" in lab_dict:
            self.ssh_port = int(lab_dict["ssh_port"])

        self.lab_capabilities = []
        if "lab_capabilities" in lab_dict:
            self.lab_capabilities = lab_dict["lab_capabilities"]

        if "horizon_url" in lab_dict:
            self.horizon_url = lab_dict["horizon_url"]
        else:
            self.horizon_url = f"https://[{self.floating_ip}]:8443/"

        if "horizon_credentials" in lab_dict:
            self.horizon_credentials = Credentials(lab_dict["horizon_credentials"])
        else:
            self.horizon_credentials = Credentials({"user_name": "admin", "password": self.admin_credentials.get_password()})

        if "rest_credentials" in lab_dict:
            self.rest_credentials = Credentials(lab_dict["rest_credentials"])
        else:
            self.rest_credentials = Credentials({"user_name": "admin", "password": self.admin_credentials.get_password()})

        self.nodes = []
        self.subclouds: List["LabConfig"] = []

        # if subclouds are listed in the config get the list with the subcloud's names.
        if "subclouds" in lab_dict:
            for subcloud in lab_dict["subclouds"]:
                subcloud_config_location = get_stx_resource_path((lab_dict["subclouds"][subcloud]))
                self.subclouds.append(LabConfig(subcloud_config_location))

        if "nodes" in lab_dict:
            for node in lab_dict["nodes"]:
                self.nodes.append(Node(node, lab_dict["nodes"][node]))

        self.ipv6 = True
        if ":" not in self.floating_ip:
            self.ipv6 = False

        self.is_dc_lab = len(self.subclouds) > 0
        # If there is a value in the config, override the above value
        if "is_dc" in lab_dict:
            self.is_dc_lab = lab_dict["is_dc"]

        self.system_controller_ip = None  # only gets set if DC system and only in the subcloud
        if "system_controller_ip" in lab_dict:
            self.system_controller_ip = lab_dict["system_controller_ip"]

        self.system_controller_name = None  # only gets set if DC system and only in the subcloud
        if "system_controller_name" in lab_dict:
            self.system_controller_name = lab_dict["system_controller_name"]

        self.secondary_system_controller = None
        if "secondary_system_controller" in lab_dict:
            secondary_system_controller = lab_dict["secondary_system_controller"]
            secondary_lab_file = get_stx_resource_path(secondary_system_controller)
            self.secondary_system_controller = LabConfig(secondary_lab_file)

        self.lab_config_file = config

    def get_floating_ip(self) -> str:
        """
        Getter for floating ip

        Returns:
            str: The floating IP address

        """
        return self.floating_ip

    def set_floating_ip(self, floating_ip: str) -> None:
        """
        Setter for floating ip

        Args:
            floating_ip (str): the host's floating ip
        """
        self.floating_ip = floating_ip

        # Update ipv4 vs ipv6 value.
        self.ipv6 = True
        if ":" not in self.floating_ip:
            self.ipv6 = False

    def get_lab_name(self) -> str:
        """
        Getter for lab name

        Returns:
            str: The lab name

        """
        return self.lab_name

    def set_lab_name(self, lab_name: str) -> None:
        """
        Setter for lab name

        Args:
            lab_name (str): the lab name
        """
        self.lab_name = lab_name

    def get_lab_type(self) -> str:
        """
        Getter for lab type

        Returns:
            str: The lab type

        """
        return self.lab_type

    def set_lab_type(self, lab_type: str) -> None:
        """
        Setter for lab type

        Args:
            lab_type (str): The lab type
        """
        self.lab_type = lab_type

    def get_admin_credentials(self) -> Credentials:
        """
        Getter for admin credentials

        Returns:
            Credentials: The admin credentials object

        """
        return self.admin_credentials

    def get_horizon_credentials(self) -> Credentials:
        """
        Getter for Horizon credentials

        Returns:
            Credentials: The Horizon credentials object

        """
        return self.horizon_credentials

    def get_rest_credentials(self) -> Credentials:
        """
        Getter for Rest credentials

        Returns:
            Credentials: The REST API credentials object

        """
        return self.rest_credentials

    def set_nodes(self, nodes: List[Node]) -> None:
        """
        Sets the labs nodes (clear any nodes already created).

        Args:
            nodes (List[Node]): The nodes to set
        """
        self.nodes = nodes

    def get_nodes(self) -> List[Node]:
        """
        Get all lab nodes.

        Returns:
            List[Node]: List of all nodes in the lab
        """
        return self.nodes

    def get_node(self, lab_node_name: str) -> Node:
        """
        Get a lab node by name.

        Args:
            lab_node_name (str): The name of the lab node ex. Controller-0

        Returns:
            Node: The lab node with the given name
        """
        for node in self.nodes:
            if node.get_name() == lab_node_name:
                return node
        return None

    def get_computes(self) -> List[Node]:
        """
        Getter for compute nodes.

        Returns:
            List[Node]: List of compute nodes
        """
        nodes = self.get_nodes()
        computes = [node for node in nodes if node.node_type == "worker"]
        return computes

    def get_compute(self, compute_name: str) -> Optional[Node]:
        """
        Retrieve an instance of Node whose type is 'Compute' and name is specified by the argument 'compute_name'.

        Args:
            compute_name (str): the name of the 'Compute' node.

        Returns:
            Optional[Node]: The compute node if found, None otherwise
        """
        computes = self.get_computes()
        compute = [compute_node for compute_node in computes if compute_node.get_name() == compute_name]
        if len(compute) > 0:
            return compute[0]
        else:
            return None

    def is_ipv6(self) -> bool:
        """
        Return True is lab is ipv6, False otherwise

        Returns:
            bool: True if IPv6 is used, False otherwise
        """
        return self.ipv6

    def get_subclouds(self) -> List["LabConfig"]:
        """
        Getter for subclouds

        Returns:
            List[LabConfig]: List of subcloud configurations
        """
        return self.subclouds

    def set_subclouds(self, subclouds: List["LabConfig"]) -> None:
        """
        Setter for subcloud

        Args:
            subclouds (List[LabConfig]): List of subcloud configurations
        """
        self.subclouds = subclouds

    def get_subcloud(self, subcloud_name: str) -> Optional["LabConfig"]:
        """
        Get a subcloud configuration by name.

        Args:
            subcloud_name (str): Name of the subcloud to retrieve

        Returns:
            Optional[LabConfig]: The subcloud configuration if found, None otherwise
        """
        for subcloud in self.subclouds:
            if subcloud.get_lab_name() == subcloud_name:
                return subcloud
        return None

    def get_subcloud_names(self) -> List[str]:
        """
        Getter for the names of the subclouds in the list of subclouds in LabConfig file.

        Args: None

        Returns:
            List[str]: List of subcloud names
        """
        return [subcloud.get_lab_name() for subcloud in self.subclouds]

    def get_horizon_url(self):
        """
        Getter for Horizon URL

        Returns: The URL to connect to Horizon

        """
        return self.horizon_url

    def set_horizon_url(self, url: str) -> None:
        """
        Setter for horizon url

        Args:
            url (str): The Horizon URL to set
        """
        self.horizon_url = url

    def is_dc(self) -> bool:
        """
        Getter for is dc

        Returns:
            bool: true if it's a dc, false otherwise
        """
        return self.is_dc_lab

    def is_use_jump_server(self) -> bool:
        """
        Getter for use jump server

        Returns:
            bool: True if jump server should be used, False otherwise
        """
        return self.use_jump_server

    def get_jump_host_configuration(self) -> HostConfiguration:
        """
        Getter for jump host configuration

        Returns:
            HostConfiguration: The jump host configuration
        """
        return self.jump_server_config

    def get_ssh_port(self) -> int:
        """
        Getter for the SSH port.

        Returns:
            int: The SSH port number
        """
        return self.ssh_port

    def get_lab_capabilities(self) -> List[str]:
        """
        Getter for lab capabilities

        Returns:
            List[str]: List of lab capabilities
        """
        return self.lab_capabilities

    def add_lab_capability(self, capability: str) -> None:
        """
        Setter for lab capability

        Args:
            capability (str): The capability to add
        """
        if capability not in self.lab_capabilities:
            self.lab_capabilities.append(capability)

    def get_lab_config_file(self) -> str:
        """
        Getter for lab config file

        Returns:
            str: Path to the lab configuration file
        """
        return self.lab_config_file

    def set_lab_config_file(self, lab_config_file: str) -> None:
        """
        Setter for lab config file

        Args:
            lab_config_file (str): Path to the lab configuration file
        """
        self.lab_config_file = lab_config_file

    def get_bm_password(self) -> str:
        """
        Getter for bm password

        Returns:
            str: The bm password
        """
        return self.bm_password

    def get_system_controller_ip(self) -> str:
        """
        Get the system controller IP address.

        Returns:
            str: The system controller IP address
        """
        return self.system_controller_ip

    def set_system_controller_ip(self, system_controller_ip: str) -> None:
        """
        Set system controller IP address.

        Args:
            system_controller_ip (str): The system controller IP address
        """
        self.system_controller_ip = system_controller_ip

    def get_system_controller_name(self) -> str:
        """
        Get the system controller name.

        Returns:
            str: The system controller name
        """
        return self.system_controller_name

    def set_system_controller_name(self, system_controller_name: str) -> None:
        """
        Setter for system_controller_name

        Args:
            system_controller_name (str): the system_controller_name
        """
        self.system_controller_name = system_controller_name

    def get_secondary_system_controller_config(self) -> object:
        """
        Get the secondary system controller object.

        Returns:
            object: Secondary dc configuration.
        """
        return self.secondary_system_controller

    def get_secondary_system_controller_name(self) -> str:
        """
        Gets the secondary controller host name

        Returns:
            str: Secondary lab name.
        """
        return self.secondary_system_controller.get_lab_name()

    def to_log_strings(self) -> List[str]:
        """
        Convert lab configuration to a list of loggable strings.

        Returns:
            List[str]: List of strings representing the lab configuration
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

    def get_controllers(self) -> List[Node]:
        """
        Getter for controller nodes.

        Returns:
            List[Node]: List of controller nodes
        """
        nodes = self.get_nodes()
        controllers = [node for node in nodes if node.node_type == "controller"]
        return controllers

    def get_subclouds_by_type(self, subcloud_type: str = None) -> List["LabConfig"]:
        """
        Get a list of subcloud configurations by type.

        Args:
            subcloud_type (str): Type of the subcloud to retrieve

        Returns:
            List[LabConfig]: List of subcloud configurations of the specified type
        """
        if subcloud_type is None:
            return self.subclouds
        return [subcloud for subcloud in self.subclouds if subcloud.get_lab_type().lower() == subcloud_type.lower()]

    def get_subclouds_name_by_type(self, subcloud_type: str = None) -> List[str]:
        """
        Get a list of subcloud names by type.

        Args:
            subcloud_type (str): Type of the subcloud to retrieve

        Returns:
            List[str]: List of subcloud names of the specified type
        """
        if subcloud_type is None:
            return [subcloud.get_lab_name() for subcloud in self.subclouds]
        return [subcloud.get_lab_name() for subcloud in self.get_subclouds_by_type(subcloud_type)]

    def get_first_controller(self) -> Optional[Node]:
        """Get the first controller node.

        Returns:
            Optional[Node]: The first controller node if found, None otherwise
        """
        controllers = self.get_controllers()
        if len(controllers) > 0:
            return controllers[0]
        return None

    def get_counterpart_controller(self, lab_node_name: str) -> Node:
        """Function to get the paired controller

        Finds and returns the counterpart controller name from a list of controllers,
        given the name of the current controller. Assumes there are exactly two controllers.

        Args:
            lab_node_name (str): The name of the current controller.

        Returns:
            Node: The counterpart / paired controller Node.
        """
        counterpart_controllers = [node for node in self.get_controllers() if node.get_name() != lab_node_name]
        if not counterpart_controllers:
            raise Exception("Others controller Not Found")
        else:
            return counterpart_controllers[0]
