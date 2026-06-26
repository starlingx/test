import copy
import os
import shlex
import shutil
from optparse import OptionParser
from typing import Optional

import json5
import yaml

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from config.deployment_assets.objects.deployment_assets import DeploymentAssets
from config.lab.objects.credentials import Credentials
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
from keywords.k8s.storageclass.kubectl_get_storageclass_keywords import KubectlGetStorageclassKeywords
from keywords.k8s.trident.kubectl_get_trident_backend_config_keywords import KubectlGetTridentBackendConfigKeywords
from keywords.linux.lspci.lspci_keywords import LspciKeywords
from testcases.conftest import log_configuration


def find_capabilities(lab_config: LabConfig) -> list[str]:
    """Find the capabilities of the given lab.

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        list[str]: A list of capabilities found in the lab.
    """
    lab_config.lab_capabilities = []
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    if query_if_lab_is_virtual(ssh_connection):
        get_logger().log_info(f"'{lab_config.get_lab_name()}' is a Virtual Lab")
        lab_config.add_lab_capability("lab_is_virtual")

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

    secondary_system_controller = lab_config.get_secondary_system_controller_config()
    if secondary_system_controller:
        lab_config.add_lab_capability("lab_has_secondary_system_controller")
        find_secondary_controller_capabilities(lab_config)

    nodes = scan_hosts(lab_config, ssh_connection)
    lab_config.set_nodes(nodes)


def query_if_lab_is_virtual(ssh_connection: SSHConnection) -> bool:
    """Query whether the lab is virtual using facter.

    Args:
        ssh_connection (SSHConnection): The SSH connection to the host.

    Returns:
        bool: True if the lab is virtual, False otherwise.
    """
    is_virtual = False
    output = ssh_connection.send(cmd="facter is_virtual")
    if isinstance(output, list):
        output = "".join(output)
    if isinstance(output, str):
        is_virtual = bool(output.strip().lower() == "true")
    return is_virtual


def find_secondary_controller_capabilities(lab_config: LabConfig):
    """Find secondary system controller capabilities from given lab.

    Args:
        lab_config (LabConfig): The lab configuration object.
    """
    try:
        secondary_system_controller = lab_config.get_secondary_system_controller_config()

        ConfigurationManager.set_lab_config(secondary_system_controller)
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

        nodes = scan_hosts(secondary_system_controller, ssh_connection)
        secondary_system_controller.set_nodes(nodes)

        lab_type = get_lab_type(secondary_system_controller)
        secondary_system_controller.set_lab_type(lab_type)

        for capability in secondary_system_controller.get_lab_capabilities():
            secondary_system_controller.add_lab_capability(capability)

        write_config(secondary_system_controller)
    finally:
        # The lab config is restored in ConfigurationManager.
        ConfigurationManager.set_lab_config(lab_config)


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

    with open(subcloud_config_file_path, "w") as config:
        config.write(get_main_lab_config(subcloud_config))


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
        ssh_connection (SSHConnection): The SSH connection to the host.

    Returns:
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
        ssh_connection (SSHConnection): The SSH connection to the host.

    Returns:
        bool: True if a matching device is found, otherwise False
    """
    lspci_keywords = LspciKeywords(ssh_connection)
    dsa_patterns = ("11fb", "0b25")
    return lspci_keywords.has_pci_device(dsa_patterns)

def has_linux_cpu_metrics(ssh_connection: SSHConnection) -> bool:
    """Verify:

     - that linux_cpu metrics exists:
     - Raise Error metrics are not present.

    Args:
        ssh_connection (SSHConnection): The SSH connection to the host.

    Returns:
        bool: True if it has linux_cpu metrics, otherwise False
    """
    output = ssh_connection.send(cmd="cpupower frequency-info")
    return not any("Not Available" in s for s in output)


def directory_exists_on_system_controller(ssh_connection: SSHConnection, directory_path: str) -> bool:
    """Check whether the given path is a directory on the system controller.

    Uses the provided SSH connection (already established with the active
    controller's floating IP by the caller) to run a read-only ``test -d``
    against the supplied path and inspects the remote return code.

    Args:
        ssh_connection (SSHConnection): An active SSH connection to the
            system controller. Must not be None.
        directory_path (str): Absolute path to check on the system
            controller. Must be a non-empty string.

    Returns:
        bool: True if the path exists and is a directory on the system
        controller, False if it does not exist, is not a directory, or the
        remote command returned an unexpected status code.

    Raises:
        ValueError: If ``ssh_connection`` is None.
        ValueError: If ``directory_path`` is None or an empty string.
    """
    if ssh_connection is None:
        raise ValueError("ssh_connection must not be None")
    if directory_path is None or directory_path == "":
        raise ValueError("directory_path must be a non-empty string")

    cmd = "test -d " + shlex.quote(directory_path)
    ssh_connection.send(cmd=cmd)
    return_code = ssh_connection.get_return_code()

    if return_code == 0:
        get_logger().log_info(f"Directory '{directory_path}' exists on system controller: True")
        return True
    if return_code == 1:
        get_logger().log_info(f"Directory '{directory_path}' exists on system controller: False")
        return False

    get_logger().log_warning(
        f"Unexpected return code '{return_code}' while checking directory '{directory_path}' on system controller; treating as not existing"
    )
    return False


def get_subcloud_basepath_from_deployment_assets(deployment_assets: DeploymentAssets) -> Optional[str]:
    """Derive the subcloud basepath from a ``DeploymentAssets`` object.

    Looks at the deployment-asset files configured for a subcloud (bootstrap,
    deployment-config, install) and returns the directory portion that they
    share. With the standard layout from
    ``config/deployment_assets/files/default.json5`` this directory is
    ``/home/sysadmin/subcloud-<N>``.

    Args:
        deployment_assets (DeploymentAssets): Deployment assets for a subcloud.

    Returns:
        Optional[str]: The basepath (directory) where the subcloud assets live,
        or ``None`` if no asset path is configured.
    """
    candidate_files = [
        deployment_assets.get_bootstrap_file() if deployment_assets.bootstrap_file else None,
        deployment_assets.get_install_file() if deployment_assets.install_file else None,
        deployment_assets.deployment_config_file,
    ]
    for path in candidate_files:
        if path:
            return os.path.dirname(path.strip())
    return None


def has_subcloud_factory_install_directory(ssh_connection: SSHConnection, deployment_assets: DeploymentAssets) -> bool:
    """Check whether the ``factory_install`` directory exists for a subcloud.

    The basepath is derived from the subcloud's deployment-asset files
    (e.g. ``/home/sysadmin/subcloud-1``); the directory looked up is
    ``<basepath>/factory_install`` on the system controller.

    Args:
        ssh_connection (SSHConnection): An active SSH connection to the system
            controller. Must not be ``None``.
        deployment_assets (DeploymentAssets): Deployment assets for the target
            subcloud. Must not be ``None`` and must expose at least one asset
            file from which the basepath can be derived.

    Returns:
        bool: ``True`` if ``<basepath>/factory_install`` exists as a directory
        on the system controller, ``False`` otherwise (including when the
        basepath cannot be derived).

    Raises:
        ValueError: If ``deployment_assets`` is ``None``.
    """
    if deployment_assets is None:
        raise ValueError("deployment_assets must not be None")

    basepath = get_subcloud_basepath_from_deployment_assets(deployment_assets)
    if not basepath:
        get_logger().log_warning("Could not derive subcloud basepath from deployment assets; cannot check 'factory_install' directory.")
        return False

    factory_install_path = os.path.join(basepath, "factory_install")
    get_logger().log_info(f"Checking factory_install directory at '{factory_install_path}'.")
    return directory_exists_on_system_controller(ssh_connection, factory_install_path)


def read_remote_install_values(ssh_connection: SSHConnection, install_values_path: str) -> Optional[dict]:
    """Read and parse a remote ``install_values.yaml`` file via SSH.

    Uses ``cat`` to fetch the file contents through the provided SSH connection
    and parses the result with ``yaml.safe_load``. The connection is expected
    to be already established with the system controller.

    Args:
        ssh_connection (SSHConnection): Active SSH connection to the system
            controller. Must not be ``None``.
        install_values_path (str): Absolute path to the ``install_values.yaml``
            file on the system controller. Must be a non-empty string.

    Returns:
        Optional[dict]: The parsed YAML content as a dict, or ``None`` if the
        file could not be read or parsed.
    """
    if ssh_connection is None:
        raise ValueError("ssh_connection must not be None")
    if not install_values_path:
        raise ValueError("install_values_path must be a non-empty string")

    cmd = f"cat {shlex.quote(install_values_path)}"
    output = ssh_connection.send(cmd=cmd)
    return_code = ssh_connection.get_return_code()
    if return_code != 0:
        get_logger().log_warning(f"Could not read remote install_values file '{install_values_path}' (rc={return_code}).")
        return None

    if isinstance(output, list):
        content = "".join(output)
    else:
        content = str(output)

    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        get_logger().log_warning(f"Failed to parse install_values file '{install_values_path}': {exc}")
        return None

    if not isinstance(parsed, dict):
        get_logger().log_warning(f"install_values file '{install_values_path}' did not parse to a mapping.")
        return None

    return parsed


def populate_subcloud_factory_credentials(
    ssh_connection: SSHConnection,
    subcloud: LabConfig,
    deployment_assets: DeploymentAssets,
) -> bool:
    """Populate ``factory_ip`` and ``factory_credentials`` on a subcloud config.

    When the subcloud's ``factory_install`` directory exists on the system
    controller, reads ``<basepath>/factory_install/<subcloud-name>-install-values.yaml``
    via SSH and copies values into the subcloud's ``LabConfig`` so they end up
    serialized in ``subcloudX.json5``:

    - ``bootstrap_address`` (in the install values file) is mapped to
      ``factory_ip`` (factory install does not expose a ``floating_ip`` key).
    - ``bmc_username`` and, when present, ``bmc_password`` are mapped to
      ``factory_credentials``. If ``bmc_password`` is missing from the file,
      an empty password is stored alongside the ``bmc_username``.

    If the ``factory_install`` directory or its install-values file is no
    longer available, any previously-stored ``factory_ip`` /
    ``factory_credentials`` are cleared so the resulting ``subcloudX.json5``
    reflects the current state of the system controller.

    Args:
        ssh_connection (SSHConnection): Active SSH connection to the system
            controller.
        subcloud (LabConfig): Subcloud configuration to update in place.
        deployment_assets (DeploymentAssets): Deployment assets for this
            subcloud, used to derive the basepath.

    Returns:
        bool: ``True`` if factory data was found and applied to the subcloud
        config, ``False`` otherwise.
    """
    if not has_subcloud_factory_install_directory(ssh_connection, deployment_assets):
        _clear_subcloud_factory_data(subcloud, reason="factory_install directory not found on system controller")
        return False

    basepath = get_subcloud_basepath_from_deployment_assets(deployment_assets)
    install_values_filename = f"{subcloud.get_lab_name()}-install-values.yaml"
    install_values_path = os.path.join(basepath, "factory_install", install_values_filename)
    install_values = read_remote_install_values(ssh_connection, install_values_path)
    if not install_values:
        _clear_subcloud_factory_data(subcloud, reason=f"install values file '{install_values_path}' could not be read")
        return False

    factory_ip = install_values.get("bootstrap_address")
    bmc_username = install_values.get("bmc_username")
    bmc_password = install_values.get("bmc_password")

    if not factory_ip or not bmc_username:
        get_logger().log_warning(
            f"install_values file '{install_values_path}' is missing 'bootstrap_address' or 'bmc_username'; "
            "factory data will not be added to the subcloud config."
        )
        _clear_subcloud_factory_data(subcloud, reason=f"install values file '{install_values_path}' is missing required keys")
        return False

    subcloud.set_factory_ip(str(factory_ip))
    password_value = "" if bmc_password is None else str(bmc_password)
    subcloud.set_factory_credentials(Credentials({"user_name": str(bmc_username), "password": password_value}))
    if not password_value:
        get_logger().log_warning(
            f"install_values file '{install_values_path}' has no 'bmc_password'; "
            f"factory_credentials.password for subcloud '{subcloud.get_lab_name()}' will be empty."
        )
    get_logger().log_info(f"Added factory data for subcloud '{subcloud.get_lab_name()}' from '{install_values_path}'.")
    return True


def _clear_subcloud_factory_data(subcloud: LabConfig, reason: str) -> None:
    """Clear ``factory_ip`` and ``factory_credentials`` from a subcloud config.

    Used when the factory install assets are no longer present on the system
    controller, so that the persisted ``subcloudX.json5`` does not keep stale
    factory information from a previous scan.

    Args:
        subcloud (LabConfig): Subcloud configuration to update in place.
        reason (str): Human-readable reason describing why the data is being
            cleared (used only for logging).
    """
    if subcloud.get_factory_ip() is None and subcloud.get_factory_credentials() is None:
        return
    get_logger().log_info(
        f"Clearing stale factory data from subcloud '{subcloud.get_lab_name()}' config ({reason})."
    )
    subcloud.set_factory_ip(None)
    subcloud.set_factory_credentials(None)


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

        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        subcloud_deployment_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)

        if subcloud_deployment_assets is not None:
            populate_subcloud_factory_credentials(ssh_connection, subcloud, subcloud_deployment_assets)

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
        system_output = GetSystemKeywords().get_system()
        system_object = system_output.get_system_object()
        if system_object.get_system_type() == "Standard":
            lab_config.add_lab_capability("lab_is_standard")
        lab_config.add_lab_capability("lab_has_standby_controller")
    else:
        raise RuntimeError("Failed to find at least one controller on this lab.")

    # Detect duplex configuration (2 controllers, no workers, no storage)
    if controllers_count == 2:
        worker_count = sum(1 for host in hosts if host.get_personality() == "worker")
        storage_count = sum(1 for host in hosts if host.get_personality() == "storage")

        if worker_count == 0 and storage_count == 0:
            lab_config.add_lab_capability("lab_is_duplex")

    # Count compute (worker) nodes and add min_N capabilities.
    compute_count = sum(1 for host in hosts if host.get_personality() == "worker")
    if compute_count >= 2:
        lab_config.add_lab_capability("lab_has_min_2_compute")
    if compute_count >= 3:
        lab_config.add_lab_capability("lab_has_min_3_compute")

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

        if host_device_output.has_host_vrb2():
            node.append_node_capability("lab_has_vrb2")
            lab_config.add_lab_capability("lab_has_vrb2")

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

        if has_linux_cpu_metrics(ssh_connection):
            node.append_node_capability("lab_has_linux_cpu_metrics")
            lab_config.add_lab_capability("lab_has_linux_cpu_metrics")
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


def get_controller_ip(host_show_output: object, controller_name: str) -> Optional[str]:
    """Get the IP address of a controller.

    Args:
        host_show_output (object): The host show output object.
        controller_name (str): The name of the controller.

    Returns:
        Optional[str]: The IP address of the controller, or None if not found.
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
    """Checks if the lab is using Rook Ceph.

    Returns:
        bool: True if the lab is using Rook Ceph, False otherwise.
    """
    backends = GetStorageBackendKeywords().get_storage_backends()
    return backends.is_backend_configured("ceph-rook")


def is_ceph() -> bool:
    """Checks if the lab is using Ceph.

    Returns:
        bool: True if the lab is using Ceph, False otherwise.
    """
    backends = GetStorageBackendKeywords().get_storage_backends()
    return backends.is_backend_configured("ceph")


def scan_storage_capabilities(lab_config: LabConfig) -> None:
    """Scan StorageClasses and TridentBackendConfigs to determine storage capabilities.

    Uses existing KubectlGetStorageclassKeywords for SC detection and
    KubectlGetTridentBackendConfigKeywords for NetApp backend health validation.

    Capabilities added:
    - lab_has_cephfs: CephFS StorageClass present
    - lab_has_netapp: At least one NetApp StorageClass present
    - lab_has_netapp_nfs: ontap-nas SC + healthy TBC
    - lab_has_netapp_iscsi: ontap-san SC + healthy TBC
    - lab_has_netapp_fc: ontap-san-fc SC + healthy TBC

    Args:
        lab_config (LabConfig): The lab configuration object.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    try:
        sc_output = KubectlGetStorageclassKeywords(ssh_connection).get_storageclasses()
    except Exception as e:
        get_logger().log_warning(f"Could not query StorageClasses: {e}")
        return

    available_types = sc_output.get_available_storage_types()
    has_netapp = False
    netapp_capabilities = []

    for storage_type in available_types:
        if storage_type == "cephfs":
            lab_config.add_lab_capability("lab_has_cephfs")
        elif storage_type == "ceph-rbd":
            lab_config.add_lab_capability("lab_has_ceph_rbd")
        elif storage_type == "netapp-nfs":
            has_netapp = True
            netapp_capabilities.append(("lab_has_netapp_nfs", "ontap-nas"))
        elif storage_type == "netapp-iscsi":
            has_netapp = True
            netapp_capabilities.append(("lab_has_netapp_iscsi", "ontap-san"))
        elif storage_type == "netapp-fc":
            has_netapp = True
            netapp_capabilities.append(("lab_has_netapp_fc", "ontap-san-fc"))

    if has_netapp:
        lab_config.add_lab_capability("lab_has_netapp")

    # Validate NetApp backends via TridentBackendConfig
    if netapp_capabilities:
        try:
            tbc_output = KubectlGetTridentBackendConfigKeywords(ssh_connection).get_trident_backend_configs()
        except Exception as e:
            get_logger().log_warning(f"Could not query TridentBackendConfigs: {e}")
            return

        for capability_name, driver_name in netapp_capabilities:
            if tbc_output.has_healthy_backend_for_driver(driver_name):
                lab_config.add_lab_capability(capability_name)
                get_logger().log_info(f"Storage capability added: {capability_name}")
            else:
                get_logger().log_warning(f"StorageClass with driver '{driver_name}' exists but no healthy TBC — " f"capability '{capability_name}' NOT added")


def write_config(lab_config: LabConfig) -> None:
    """
    Writes the new config out to the current config

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        None:
    """
    config_dict = _build_config_dict(lab_config)

    lab_config_file = lab_config.get_lab_config_file()
    shutil.move(lab_config_file, f"{lab_config_file}_bak")
    with open(lab_config_file, "w") as config:
        config.write(json5.dumps(config_dict, indent=4))


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


def _build_config_dict(lab_config: LabConfig) -> dict:
    """Build a plain Python dict representing the full lab configuration.

    Using a dict and delegating serialization to json5.dumps means all values
    (including file paths with backslashes) are escaped correctly without any
    manual string manipulation.

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        dict: The lab configuration as a serializable dictionary.
    """
    config = {
        "floating_ip": lab_config.get_floating_ip(),
        "lab_name": lab_config.get_lab_name(),
        "lab_type": lab_config.get_lab_type(),
        "admin_credentials": {
            "user_name": lab_config.get_admin_credentials().get_user_name(),
            "password": lab_config.get_admin_credentials().get_password(),
        },
        "bm_password": lab_config.get_bm_password(),
        "use_jump_server": lab_config.is_use_jump_server(),
    }

    if lab_config.is_use_jump_server():
        config["jump_server_config"] = lab_config.get_jump_host_configuration().get_host_config_file()

    if lab_config.get_ssh_port():
        config["ssh_port"] = lab_config.get_ssh_port()

    config["horizon_url"] = lab_config.get_horizon_url()

    if lab_config.get_system_controller_ip():
        config["system_controller_ip"] = lab_config.get_system_controller_ip()

    if lab_config.get_system_controller_name():
        config["system_controller_name"] = lab_config.get_system_controller_name()

    if lab_config.get_factory_ip():
        config["factory_ip"] = lab_config.get_factory_ip()

    if lab_config.get_factory_credentials():
        config["factory_credentials"] = {
            "user_name": lab_config.get_factory_credentials().get_user_name(),
            "password": lab_config.get_factory_credentials().get_password(),
        }

    config["lab_capabilities"] = lab_config.get_lab_capabilities()

    if lab_config.get_nodes():
        config["nodes"] = {
            node.get_name(): {
                "ip": node.get_ip(),
                "node_type": node.get_type(),
                "bm_ip": node.get_bm_ip(),
                "bm_username": node.get_bm_username(),
                "node_capabilities": node.get_node_capabilities(),
            }
            for node in lab_config.get_nodes()
        }

    if lab_config.get_subclouds():
        subclouds_sorted = sorted(lab_config.get_subclouds(), key=lambda sc: sc.get_lab_name())
        config["subclouds"] = {sc.get_lab_name(): sc.get_lab_config_file() for sc in subclouds_sorted}

    secondary = lab_config.get_secondary_system_controller_config()
    if secondary:
        config["secondary_system_controller"] = secondary.get_lab_config_file()

    return config


def get_main_lab_config(lab_config: LabConfig) -> str:
    """
    Gets the configuration lines for the 'main' lab.

    Args:
        lab_config (LabConfig): The lab configuration object.

    Returns:
        str: The formatted configuration for the main lab.

    Note:
        Kept for use by create_subcloud_config_file_if_needed. Delegates to
        _build_config_dict so all escaping is handled by json5.dumps.
    """
    config = _build_config_dict(lab_config)
    # Strip nodes/subclouds/secondary — this function is only used to seed a
    # new subcloud stub file which doesn't have those yet.
    config.pop("nodes", None)
    config.pop("subclouds", None)
    config.pop("secondary_system_controller", None)
    return json5.dumps(config, indent=4)


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
        lab_config.add_lab_capability("lab_has_ceph_rbd")

    # check if the lab is using ceph
    if is_ceph():
        lab_config.add_lab_capability("lab_has_ceph")

    # check storage capabilities from StorageClass and TridentBackendConfig
    scan_storage_capabilities(lab_config)

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
