import copy
import os
import shutil
from optparse import OptionParser

import json5

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_config import LabConfig
from config.lab.objects.node import Node
from framework.database.objects.lab_capability import LabCapability
from framework.database.operations.capability_operation import CapabilityOperation
from framework.database.operations.lab_capability_operation import LabCapabilityOperation
from framework.database.operations.lab_operation import LabOperation
from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from keywords.bmc.ipmitool.is_ipmitool_keywords import IsIPMIToolKeywords
from keywords.bmc.ipmitool.sensor.ipmitool_sensor_keywords import IPMIToolSensorKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_management_enum import DcManagerSubcloudListManagementEnum
from keywords.cloud_platform.rest.bare_metal.disks.get_host_disks_keywords import GetHostDisksKeywords
from keywords.cloud_platform.rest.bare_metal.hosts.get_hosts_cpus_keywords import GetHostsCpusKeywords
from keywords.cloud_platform.rest.bare_metal.hosts.get_hosts_keywords import GetHostsKeywords
from keywords.cloud_platform.rest.bare_metal.memory.get_host_memory_keywords import GetHostMemoryKeywords
from keywords.cloud_platform.rest.bare_metal.ports.get_host_ports_keywords import GetHostPortsKeywords
from keywords.cloud_platform.rest.configuration.addresses.get_host_addresses_keywords import GetHostAddressesKeywords
from keywords.cloud_platform.rest.configuration.devices.system_host_device_keywords import GetHostDevicesKeywords
from keywords.cloud_platform.rest.configuration.interfaces.get_interfaces_keywords import GetInterfacesKeywords
from keywords.cloud_platform.rest.configuration.storage.get_storage_backends_keyword import GetStorageBackendKeywords
from keywords.cloud_platform.rest.configuration.storage.get_storage_keywords import GetStorageKeywords
from keywords.cloud_platform.rest.configuration.system.get_system_keywords import GetSystemKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.objects.system_host_if_output import SystemHostInterfaceOutput
from keywords.cloud_platform.system.oam.objects.system_oam_show_output import SystemOamShowOutput
from keywords.cloud_platform.system.oam.system_oam_show_keywords import SystemOamShowKeywords
from testcases.conftest import log_configuration
from keywords.linux.lspci.lspci_keywords import LspciKeywords

def find_capabilities(lab_config: LabConfig) -> list[str]:
    """Find the capabilities of the given lab.

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        list[str]: A list of capabilities found in the lab.
    """
    lab_config.lab_capabilities = []

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config.set_horizon_url(get_horizon_url())

    # Check if this is a DC system by checking distributed_cloud_role
    system_output = GetSystemKeywords().get_system()
    system_object = system_output.get_system_object()
    is_dc_system = system_object.get_distributed_cloud_role() == "systemcontroller"
    if is_dc_system:
        subclouds = retrieve_subclouds(lab_config, ssh_connection)
        lab_config.set_subclouds(subclouds[:])
        find_subclouds_capabilities(lab_config)

    if len(lab_config.get_subclouds()) != 0:
        lab_config.add_lab_capability("lab_has_subcloud")

    if len(lab_config.get_subclouds()) >= 2:
        lab_config.add_lab_capability("lab_has_min_2_subclouds")

    nodes = scan_hosts(lab_config, ssh_connection)
    lab_config.set_nodes(nodes)


def find_subclouds_capabilities(lab_config: LabConfig) -> list[str]:
    """Find the capabilities of the subclouds from the given lab.

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        list[str]: A list of capabilities found in the subclouds.
    """
    if len(lab_config.get_subclouds()) == 0:
        return

    subclouds: list[LabConfig] = lab_config.get_subclouds()
    try:
        for subcloud in subclouds:

            # The subcloud config is set as lab config in ConfigurationManager just for time of this iteration.
            ConfigurationManager.set_lab_config(subcloud)
            ssh_connection_to_subcloud = LabConnectionKeywords().get_active_controller_ssh()  # This is the active controller of the subcloud

            nodes = scan_hosts(subcloud, ssh_connection_to_subcloud)
            subcloud.set_nodes(nodes)

            lab_type = get_lab_type(subcloud)
            subcloud.set_lab_type(lab_type)

            for capability in subcloud.get_lab_capabilities():
                lab_config.add_lab_capability(f"subcloud_{capability}")

            write_config(subcloud)
    finally:
        # The lab config is restored in ConfigurationManager.
        ConfigurationManager.set_lab_config(lab_config)


def get_subcloud_name_from_path(subcloud_config_file_path: str) -> str:
    """Extract the subcloud name from a config file path.

    Args:
        subcloud_config_file_path (str): The subcloud config file path.

    Returns:
        str: The name of the subcloud.
    """
    _, subcloud_config_filename = os.path.split(subcloud_config_file_path)
    subcloud_name, _ = os.path.splitext(subcloud_config_filename)
    return subcloud_name


def create_subcloud_config_file_if_needed(host: LabConfig, subcloud_name: str, subcloud_config_file_path: str) -> None:
    """Create a new config file for the subcloud if it doesn't exist.

    Args:
        host (LabConfig): The host lab configuration.
        subcloud_name (str): The name of the subcloud.
        subcloud_config_file_path (str): The subcloud's config file path.

    Note:
        The initial content is based on the host config but with empty IP.
    """
    if os.path.isfile(subcloud_config_file_path):
        return

    subcloud_config = copy.deepcopy(host)
    subcloud_config.set_floating_ip("")
    subcloud_config.set_lab_name(subcloud_name)

    new_config = "{"
    new_config += get_main_lab_config(subcloud_config)
    new_config += "}"

    with open(subcloud_config_file_path, "w") as config:
        config.write(json5.dumps(json5.loads(new_config), indent=4))


def is_sriov(host_interface_list_output: SystemHostInterfaceOutput) -> bool:
    """Check if SR-IOV is enabled on the given node.

    Args:
        host_interface_list_output (SystemHostInterfaceOutput): Output of the system host interface list command.

    Returns:
        bool: True if SR-IOV is enabled, False otherwise.
    """
    sriov_list: [] = host_interface_list_output.get_interfaces_by_class("pci-sriov")
    if len(sriov_list) > 0:
        return True
    return False


def has_host_bmc_sensor(ssh_connection: SSHConnection) -> bool:
    """Check if the node has BMC sensors.

    Args:
        ssh_connection (SSHConnection): The SSH connection to the host.

    Returns:
        bool: True if the node has BMC sensors, False otherwise.
    """
    # First check if the lab has ipmitool available.
    is_ipmi_tool_available = IsIPMIToolKeywords(ssh_connection).is_ipmi_tool_available()
    if not is_ipmi_tool_available:
        return False

    # Check if there is at least one sensor.
    ipmitool_sensor_output = IPMIToolSensorKeywords(ssh_connection).get_ipmi_tool_sensor_list()
    return len(ipmitool_sensor_output) > 0


def has_qat_device(ssh_connection: SSHConnection) -> bool:
    """Verify:
     - that the QAT Device exists: 4940|4942|0b40
     - Raise Error If Above Devices are not present.
    Args:
        ssh_connection: SSHConnection object
    Return:
        bool: True if a matching device is found, otherwise False
    """
    lspci_keywords = LspciKeywords(ssh_connection)
    qat_patterns = ("4940", "4942", "0b40")

    return lspci_keywords.has_pci_device(qat_patterns)

def has_dsa_device(ssh_connection: SSHConnection) -> bool:
    """Verify:
     - that the DSA Device exists: 11fb|0b25
     - Raise Error If Above Devices are not present.
    Args:
        ssh_connection: SSHConnection object
    Return:
        bool: True if a matching device is found, otherwise False
    """
    lspci_keywords = LspciKeywords(ssh_connection)
    dsa_patterns = ("11fb","0b25")
    return  lspci_keywords.has_pci_device(dsa_patterns)


def retrieve_subclouds(lab_config: LabConfig, ssh_connection: SSHConnection) -> list[LabConfig]:
    """Get the list of online and managed subclouds.
    Only subclouds with 'availability' = 'online' and 'management' = 'managed' are considered.

    Args:
        lab_config (LabConfig): The lab config object.
        ssh_connection (SSHConnection): Connection to the active controller of the central cloud.

    Returns:
        list[LabConfig]: List of LabConfig objects for online and managed subclouds.
    """
    subclouds: [LabConfig] = []

    lab_config_directory = os.path.split(lab_config.get_lab_config_file())[0]  # get the config directory

    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
    dcmanager_subclouds = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list()

    for dcmanager_subcloud in dcmanager_subclouds.get_dcmanager_subcloud_list_objects():

        subcloud_name = dcmanager_subcloud.get_name()

        if dcmanager_subcloud.get_availability() != DcManagerSubcloudListAvailabilityEnum.ONLINE.value or dcmanager_subcloud.get_management() != DcManagerSubcloudListManagementEnum.MANAGED.value:
            get_logger().log_info(f"Subcloud {subcloud_name} will not be scanned because it is not {DcManagerSubcloudListAvailabilityEnum.ONLINE.value} and {DcManagerSubcloudListManagementEnum.MANAGED.value}.")
            continue

        subcloud_config_file_path = f"{lab_config_directory}/{subcloud_name}.json5"
        create_subcloud_config_file_if_needed(lab_config, subcloud_name, subcloud_config_file_path)
        subcloud = LabConfig(subcloud_config_file_path)
        subcloud_ip = get_subcloud_ip(subcloud_name, ssh_connection)
        if subcloud_ip is None:
            get_logger().log_info(f"It was not possible to find an accessible IP for subcloud: {subcloud_name}.")
            continue

        subcloud.set_floating_ip(subcloud_ip)
        subcloud.set_system_controller_ip(lab_config.get_floating_ip())
        subcloud.set_system_controller_name(lab_config.get_lab_name())

        subclouds.append(subcloud)

    return subclouds


def get_subcloud_ip(subcloud_name: str, central_cloud_ssh_connection: SSHConnection) -> str:
    """Get the external IP address of a subcloud.

    Args:
        subcloud_name (str): The name of the subcloud.
        central_cloud_ssh_connection (SSHConnection): SSH connection to the central cloud.

    Returns:
        str: The subcloud's IP address.
    """
    # Executes the command 'system oam-show' on the subcloud to get the subcloud's IP.
    password_prompt = PromptResponse("password:", ConfigurationManager.get_lab_config().get_admin_credentials().get_password())
    open_rc_prompt = PromptResponse("~$", "source /etc/platform/openrc")
    system_oam_show_prompt = PromptResponse("]$", "system oam-show")
    end_prompt = PromptResponse("@")

    expected_prompts = [password_prompt, open_rc_prompt, system_oam_show_prompt, end_prompt]

    system_oam_show_output_list = central_cloud_ssh_connection.send_expect_prompts(f"ssh {subcloud_name} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no", expected_prompts)
    system_oam_show_output: SystemOamShowOutput = SystemOamShowOutput(system_oam_show_output_list)

    # Get the oam_ip if available (used in vbox environments).
    subcloud_ip = system_oam_show_output.system_oam_show_object.get_oam_ip()
    # If oam_ip is not available, fall back to oam_floating_ip (used in physical labs).
    if not subcloud_ip:
        subcloud_ip = system_oam_show_output.system_oam_show_object.get_oam_floating_ip()

    return subcloud_ip


def get_nodes(lab_config: LabConfig) -> list[Node]:
    """
    Gets the nodes on this lab.

    Args:
        lab_config (LabConfig): The lab config object.

    Returns:
        list[Node]: list of Nodes.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    return scan_hosts(lab_config, ssh_connection)


def scan_hosts(lab_config: LabConfig, ssh_connection: SSHConnection) -> list[Node]:
    """
    Scans the nodes on this lab and return a list of Nodes.

    Args:
        lab_config (LabConfig): the lab config object.
        ssh_connection (SSHConnection): The SSH connection to the host one wants to scan.

    Returns:
        list[Node]: list of Nodes.

    Raises:
        RuntimeError: If no controller node is found in the lab.
    """
    host_show_output = GetHostsKeywords().get_hosts()
    hosts = host_show_output.get_all_system_host_show_objects()
    nodes = []

    # Count the controllers to decide if the lab is Simplex or not.
    controllers_count = 0
    for host in hosts:
        if host.get_personality() == "controller":
            controllers_count += 1

    if controllers_count == 1:
        lab_config.add_lab_capability("lab_is_simplex")
    elif controllers_count > 1:
        lab_config.add_lab_capability("lab_has_standby_controller")
    else:
        raise RuntimeError("Failed to find at least one controller on this lab.")

    # Look at the Capabilities of each host individually.
    for host in hosts:

        name = host.get_hostname()
        node_dict = {
            "ip": get_controller_ip(host_show_output, name),
            "node_type": host.get_personality(),
            "node_capabilities": [],
        }
        node = Node(host.get_hostname(), node_dict)

        node.set_subfunctions(host.get_subfunctions())
        node.set_bm_username(host.get_bm_username())
        node.set_bm_ip(host.get_bm_ip())

        # Gather data from the system into objects.

        host_uuid = host_show_output.get_system_host_show_object(node.get_name()).get_uuid()

        host_cpu_output = GetHostsCpusKeywords().get_hosts_cpus(host_uuid)
        host_interface_list_output = GetInterfacesKeywords().get_interfaces(host_uuid)
        host_device_output = GetHostDevicesKeywords().get_devices(host_uuid)
        host_port_output = GetHostPortsKeywords().get_ports(host_uuid)
        host_memory_output = GetHostMemoryKeywords().get_memory(host_uuid)
        host_storage_output = GetStorageKeywords().get_storage(host_uuid)
        host_disk_output = GetHostDisksKeywords().get_disks(host_uuid)

        # Parse the data to define the lab's capabilities.
        if is_sriov(host_interface_list_output):
            node.append_node_capability("lab_has_sriov")
            lab_config.add_lab_capability("lab_has_sriov")

        if node.get_type() == "worker":
            node.append_node_capability("lab_has_compute")
            lab_config.add_lab_capability("lab_has_compute")

        if node.get_type() == "worker" or "worker" in node.get_subfunctions():
            node.append_node_capability("lab_has_worker")
            lab_config.add_lab_capability("lab_has_worker")

        if node.get_type() == "storage":
            node.append_node_capability("lab_has_storage")
            lab_config.add_lab_capability("lab_has_storage")

        if "lowlatency" in node.get_subfunctions():
            node.append_node_capability("lab_has_low_latency")
            lab_config.add_lab_capability("lab_has_low_latency")
        else:
            node.append_node_capability("lab_has_non_low_latency")
            lab_config.add_lab_capability("lab_has_non_low_latency")

        if host_cpu_output.is_host_hyperthreaded():
            node.append_node_capability("lab_has_hyperthreading")
            lab_config.add_lab_capability("lab_has_hyperthreading")
        else:
            node.append_node_capability("lab_has_no_hyperthreading")
            lab_config.add_lab_capability("lab_has_no_hyperthreading")

        if lab_config.is_ipv6():
            node.append_node_capability("lab_is_ipv6")
            lab_config.add_lab_capability("lab_is_ipv6")
        else:
            node.append_node_capability("lab_is_ipv4")
            lab_config.add_lab_capability("lab_is_ipv4")

        if host_device_output.has_host_n3000():
            node.append_node_capability("lab_has_n3000")
            lab_config.add_lab_capability("lab_has_n3000")

        if host_device_output.has_host_fpga():
            node.append_node_capability("lab_has_fpga")
            lab_config.add_lab_capability("lab_has_fpga")

        if host_device_output.has_host_acc100():
            node.append_node_capability("lab_has_acc100")
            lab_config.add_lab_capability("lab_has_acc100")

        if host_device_output.has_host_acc200():
            node.append_node_capability("lab_has_acc200")
            lab_config.add_lab_capability("lab_has_acc200")

        if host_port_output.has_host_columbiaville():
            node.append_node_capability("lab_has_columbiaville")
            lab_config.add_lab_capability("lab_has_columbiaville")

        if host_disk_output.has_minimum_disk_space_in_gb(30):
            node.append_node_capability("lab_has_min_space_30G")
            lab_config.add_lab_capability("lab_has_min_space_30G")

        if host_cpu_output.has_minimum_number_processors(2):
            node.append_node_capability("lab_has_processor_min_2")
            lab_config.add_lab_capability("lab_has_processor_min_2")

        if host_memory_output.has_page_size_1gb():
            node.append_node_capability("lab_has_page_size_1gb")
            lab_config.add_lab_capability("lab_has_page_size_1gb")

        if host_interface_list_output.has_ae_interface():
            node.append_node_capability("lab_has_ae_interface")
            lab_config.add_lab_capability("lab_has_ae_interface")

        if host_interface_list_output.has_minimum_number_physical_interface(2):
            node.append_node_capability("lab_has_physical_interface_min_2")
            lab_config.add_lab_capability("lab_has_physical_interface_min_2")

        if host_interface_list_output.has_bond_interface():
            node.append_node_capability("lab_has_bond_interface")
            lab_config.add_lab_capability("lab_has_bond_interface")

        if host_storage_output.has_minimum_number_physical_interface(6):
            node.append_node_capability("lab_has_storage_6_osd")
            lab_config.add_lab_capability("lab_has_storage_6_osd")

        if host_show_output.has_host_bmc_ipmi(name):
            node.append_node_capability("lab_has_bmc_ipmi")
            lab_config.add_lab_capability("lab_has_bmc_ipmi")

        elif host_show_output.has_host_bmc_redfish(name):
            node.append_node_capability("lab_has_bmc_redfish")
            lab_config.add_lab_capability("lab_has_bmc_redfish")

        elif host_show_output.has_host_bmc_dynamic(name):
            node.append_node_capability("lab_has_bmc_dynamic")
            lab_config.add_lab_capability("lab_has_bmc_dynamic")

        if has_host_bmc_sensor(ssh_connection):
            node.append_node_capability("lab_bmc_sensor")
            lab_config.add_lab_capability("lab_bmc_sensor")

        if has_qat_device(ssh_connection):
            node.append_node_capability("lab_has_qat")
            lab_config.add_lab_capability("lab_has_qat")

        if has_dsa_device(ssh_connection):
            node.append_node_capability("lab_has_dsa")
            lab_config.add_lab_capability("lab_has_dsa")
        nodes.append(node)
    return nodes


def _matches_ip_version(ip_address: str, is_ipv6_lab: bool) -> bool:
    """Check if IP address matches the lab's IP version configuration.

    Args:
        ip_address (str): The IP address to check.
        is_ipv6_lab (bool): Whether the lab is configured for IPv6.

    Returns:
        bool: True if IP version matches lab configuration.
    """
    is_ipv6_address = ":" in ip_address
    return is_ipv6_lab == is_ipv6_address


def get_controller_ip(host_show_output: object, controller_name: str) -> str | None:
    """Get the IP address of a controller.

    Args:
        host_show_output (object): The host show output object.
        controller_name (str): The name of the controller.

    Returns:
        str | None: The IP address of the controller, or None if not found.
    """
    host_object = host_show_output.get_system_host_show_object(controller_name)
    host_uuid = host_object.get_uuid()

    if host_uuid is None:
        get_logger().log_error(f"Host {controller_name} not found")
        return None

    host_interface_list_output = GetInterfacesKeywords().get_interfaces(host_uuid)
    host_addresses_output = GetHostAddressesKeywords().get_host_addresses(host_uuid)
    lab_config = ConfigurationManager.get_lab_config()
    is_ipv6_lab = lab_config.is_ipv6()

    if host_object.get_personality() == "controller":
        # For controllers, get OAM interface from all platform interfaces
        platform_interfaces = host_interface_list_output.get_interfaces_by_class("platform")
        if not platform_interfaces:
            raise RuntimeError(f"No platform interfaces found for controller {controller_name}")

        # First try OAM interfaces specifically
        for interface in platform_interfaces:
            if "oam" in interface.get_name():
                controller_ip = host_addresses_output.get_address_by_ifname(interface.get_name())
                if controller_ip and _matches_ip_version(controller_ip, is_ipv6_lab):
                    return controller_ip

        # Fallback to any platform interface with matching IP version
        for interface in platform_interfaces:
            controller_ip = host_addresses_output.get_address_by_ifname(interface.get_name())
            if controller_ip and _matches_ip_version(controller_ip, is_ipv6_lab):
                return controller_ip

        raise RuntimeError(f"No matching IP address found for controller {controller_name}")
    else:
        # For compute nodes, get management interface
        platform_interfaces = host_interface_list_output.get_interfaces_by_class("platform")
        for interface in platform_interfaces:
            if interface.get_name().startswith("mgmt"):
                mgmt_ip = host_addresses_output.get_address_by_ifname(interface.get_name())
                if mgmt_ip and _matches_ip_version(mgmt_ip, is_ipv6_lab):
                    return mgmt_ip

        return None


def get_horizon_url() -> str:
    """Get the Horizon URL using system CLI commands.

    Returns:
        str: The formatted Horizon URL.
    """
    # Get system capabilities to check if HTTPS is enabled
    system_output = GetSystemKeywords().get_system()
    system_capabilities = system_output.get_system_object().get_capabilities()
    https_enabled = system_capabilities.get_https_enabled() if system_capabilities else False

    # Get OAM IP information using system CLI
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    oam_show_output = SystemOamShowKeywords(ssh_connection).oam_show()

    # Get the appropriate IP (oam_ip for vbox, oam_floating_ip for physical)
    oam_ip = oam_show_output.get_oam_ip() or oam_show_output.get_oam_floating_ip()

    # Construct Horizon URL
    protocol = "https" if https_enabled else "http"
    port = "8443" if https_enabled else "8080"

    wrapped_ip = oam_ip
    if ":" in oam_ip:
        wrapped_ip = f"[{oam_ip}]"

    return f"{protocol}://{wrapped_ip}:{port}/"


def get_lab_type(lab_config: LabConfig) -> str:
    """
    Gets the lab type

    Args:
        lab_config (LabConfig): the lab config.

    Returns:
        str: the lab type
    """
    # if lab has subclouds, then it's a DC
    if len(lab_config.get_subclouds()) > 0:
        return "DC"

    nodes = lab_config.get_nodes()

    controller_nodes = list(filter(lambda node: node.get_type() == "controller", nodes))
    worker_nodes = list(filter(lambda node: node.get_type() == "worker", nodes))
    storage_nodes = list(filter(lambda node: node.get_type() == "storage", nodes))

    if len(controller_nodes) < 2:
        return "Simplex"
    # if we have storage nodes or compute nodes and the controllers have work subfunction, then AIO+
    if (len(storage_nodes) > 0 or len(worker_nodes) > 0) and len(list(filter(lambda controller: "worker" in controller.get_subfunctions(), controller_nodes))) > 1:
        return "AIO+"
    if len(storage_nodes) > 0:
        return "Storage"
    if len(worker_nodes) > 0:
        return "Standard"
    # more than 2 controller but no computes or storage == Duplex
    return "Duplex"


def is_aio(lab_config: LabConfig) -> bool:
    """Checks if the lab is AIO.

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        bool: True if the lab is AIO, False otherwise.
    """
    nodes = lab_config.get_nodes()
    worker_nodes = list(filter(lambda node: node.get_type() == "worker", nodes))

    return len(worker_nodes) == 0


def is_rook_ceph() -> bool:
    """
    Checks if the lab is using Rook Ceph.

    Returns:
        bool: True if the lab is using Rook Ceph, False otherwise.
    """
    backends = GetStorageBackendKeywords().get_storage_backends()
    return backends.is_backend_configured("ceph-rook")


def write_config(lab_config: LabConfig) -> None:
    """
    Writes the new config out to the current config

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        None:
    """
    new_config = "{"
    new_config += get_main_lab_config(lab_config)
    new_config += get_nodes_config(lab_config)
    new_config += get_subclouds_config(lab_config)
    new_config += "}"

    lab_config_file = lab_config.get_lab_config_file()
    shutil.move(lab_config_file, f"{lab_config_file}_bak")
    with open(lab_config_file, "w") as config:
        config.write(json5.dumps(json5.loads(new_config), indent=4))


def clean_subcloud_config_files(lab_config: LabConfig) -> None:
    """
    Clears config files created during the scan process that are not useful anymore.

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        None:
    """
    lab_config_file = lab_config.get_lab_config_file()
    lab_config_directory, _ = os.path.split(lab_config_file)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(ssh_connection)
    dcmanager_subclouds = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list()

    for dcmanager_subcloud in dcmanager_subclouds.get_dcmanager_subcloud_list_objects():
        subcloud_name = dcmanager_subcloud.get_name()
        subcloud_file_name = f"{subcloud_name}.json5"
        subcloud_backup_name = f"{subcloud_name}.json5_bak"
        subcloud_file_path = os.path.join(lab_config_directory, subcloud_file_name)
        subcloud_backup_path = os.path.join(lab_config_directory, subcloud_backup_name)
        if os.path.exists(subcloud_file_path):
            subcloud_lab_config = LabConfig(subcloud_file_path)
            if subcloud_lab_config.get_floating_ip() == "":
                os.remove(subcloud_file_path)
        if os.path.exists(subcloud_backup_path):
            subcloud_lab_config = LabConfig(subcloud_backup_path)
            if subcloud_lab_config.get_floating_ip() == "":
                os.remove(subcloud_backup_path)


def get_main_lab_config(lab_config: LabConfig) -> str:
    """
    Gets the configuration lines for the 'main' lab.

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        str: The formatted configuration for the main lab.
    """
    main_config = f'floating_ip: "{lab_config.get_floating_ip()}",'
    main_config += f'lab_name: "{lab_config.get_lab_name()}",'
    main_config += f'lab_type: "{lab_config.get_lab_type()}",'
    main_config += "admin_credentials: {"
    main_config += f'user_name: "{lab_config.get_admin_credentials().get_user_name()}",'
    main_config += f'password: "{lab_config.get_admin_credentials().get_password()}",'
    main_config += "},"
    main_config += f'bm_password: "{lab_config.get_bm_password()}",'
    use_jump_server = "true" if lab_config.is_use_jump_server() else "false"
    main_config += f"use_jump_server: {use_jump_server},"
    if lab_config.is_use_jump_server():
        main_config += f'jump_server_config: "{lab_config.get_jump_host_configuration().get_host_config_file()}",'
    if lab_config.get_ssh_port():
        main_config += f"ssh_port: {lab_config.get_ssh_port()},"
    main_config += f'horizon_url: "{lab_config.get_horizon_url()}",'
    if lab_config.get_system_controller_ip():
        main_config += f'system_controller_ip: "{lab_config.get_system_controller_ip()}",'
    if lab_config.get_system_controller_name():
        main_config += f'system_controller_name: "{lab_config.get_system_controller_name()}",'
    lab_capabilities_as_str = ", \n".join('"{}"'.format(capability) for capability in lab_config.get_lab_capabilities())
    main_config += f'"lab_capabilities": [\n{lab_capabilities_as_str}],\n'

    return main_config


def get_nodes_config(lab_config: LabConfig) -> str:
    """
    Retrieves the configuration settings for the nodes.

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        str: The formatted configuration for the nodes.
    """
    if not lab_config.get_nodes():
        return ""

    node_config = '"nodes": {'
    for node in lab_config.get_nodes():
        node_config += f'"{node.get_name()}": ' + "{"
        node_config += f'"ip": "{node.get_ip()}",'
        node_config += f'"node_type": "{node.get_type()}",'
        node_config += f'"bm_ip": "{node.get_bm_ip()}",'
        node_config += f'"bm_username": "{node.get_bm_username()}",'
        node_capabilities_as_str = ", \n".join('"{}"'.format(capability) for capability in node.get_node_capabilities())
        node_config += f'"node_capabilities": [\n{node_capabilities_as_str}],\n'
        node_config += "},"
    node_config += "},"

    return node_config


def get_subclouds_config(lab_config: LabConfig) -> str:
    """
    Getter for the subcloud configs (the portion in lab config file where are specified the subcloud config file paths).

    Args:
        lab_config (LabConfig): The subcloud LabConfig object.

    Returns:
        str: The formatted subcloud configuration.
    """
    if not lab_config.get_subclouds():
        return ""

    subcloud_config = '"subclouds": {'
    subclouds: list[LabConfig] = lab_config.get_subclouds()
    subclouds_sorted = sorted(subclouds, key=lambda subcloud: subcloud.get_lab_name())
    for subcloud in subclouds_sorted:
        subcloud_config += f'"{subcloud.get_lab_name()}": "{subcloud.get_lab_config_file()}",'
    subcloud_config += "}"

    return subcloud_config


if __name__ == "__main__":
    """
    This Function will update the given configuration with a list of capabilities. It scans the current lab
    for known capabilities and adds them.

    Usage Example:
        python3 lab_capability_scanner.py --lab_config_file=config/lab/files/default.json5"

    Args:
        --lab_config_file (str): the location of the lab config
    """

    configuration_locations_manager = ConfigurationFileLocationsManager()

    # add an option for floating ip on command line
    parser = OptionParser()

    parser.add_option("--floating_ip", action="store", type="str", dest="floating_ip", help="The floating ip of the lab if overriding the config")
    configuration_locations_manager.set_configs_from_options_parser(parser)

    ConfigurationManager.load_configs(configuration_locations_manager)
    log_configuration()

    lab_config = ConfigurationManager.get_lab_config()

    # check if a floating ip was set on commandline, if so override default config
    options, args = parser.parse_args()
    if options.floating_ip:
        lab_config.set_floating_ip(options.floating_ip)

    find_capabilities(lab_config)

    # find the lab_type
    lab_type = get_lab_type(lab_config)
    lab_config.set_lab_type(lab_type)

    # check if the lab is an aio
    if is_aio(lab_config):
        lab_config.add_lab_capability("lab_is_aio")

    # check if the lab is using rook ceph
    if is_rook_ceph():
        lab_config.add_lab_capability("lab_has_rook_ceph")

    if ConfigurationManager.get_database_config().use_database():
        # insert lab into db if it doesn't already exist
        lab_name = lab_config.get_lab_name()
        lab_operation = LabOperation()
        if not lab_operation.does_lab_exist(lab_name):
            lab_operation.insert_lab(lab_name)

        lab_info_id = lab_operation.get_lab_id(lab_name)

        # delete current capabilities
        lab_capability_operation = LabCapabilityOperation()
        lab_capability_operation.delete_all_lab_capabilities(lab_info_id)

        capability_operation = CapabilityOperation()
        # add capability mappings
        for capability in lab_config.get_lab_capabilities():
            capability_id = capability_operation.get_capability_by_marker(capability).get_capability_id()
            if capability_id == -1:
                get_logger().log_error(f"No capability found with the name {capability} in the database")
            else:
                lab_capability = LabCapability(-1, lab_info_id, capability_id)  # -1 since we don't have a lab capability id yet
                lab_capability_operation.insert_lab_capability(lab_capability)

    write_config(lab_config)
    if "lab_has_subcloud" in lab_config.get_lab_capabilities():
        clean_subcloud_config_files(lab_config)
