"""Subcloud deployment with external registry route injection.

Deploys subclouds using phased deployment (create, install, bootstrap, config)
with NAT64 route injection between install and bootstrap phases. This enables
subclouds on IPv6 networks to pull container images from an external registry
during bootstrap.

The test configures the subcloud's bootstrap values with the system controller's
docker_registries config, injects the NAT64 route after install-complete, and
restores the original bootstrap values in teardown.

Prerequisites:
    - System controller is accessible (--lab_config_file)
    - System controller has a working NAT64 route to the external registry
    - Deployment assets synced to system controller

Run with:
    pytest starlingx/testcases/cloud_platform/regression/dc/deployment/test_deploy_subcloud_external_registry.py \
        --lab_config_file=<LAB_CONFIG> \
        --deployment_assets_config_file=<DEPLOYMENT_ASSETS_CONFIG> -v -s

Markers:
    - @mark.lab_has_subcloud: Requires at least one subcloud in config
    - @mark.subcloud_lab_is_ipv6: Only runs on IPv6 labs (NAT64 route needed)
"""

from typing import List

from pytest import mark
from pytest import FixtureRequest

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.dcmanager.bootstrap_values_keywords import BootstrapValuesKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_lifecycle_keywords import DcManagerSubcloudLifecycleKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords, pick_subcloud_with_fallback
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sync_files.sync_deployment_assets import SyncDeploymentAssets
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.linux.ip.ip_route_keywords import IPRouteKeywords

# Path to the central cloud's bootstrap values (used to source registry config)
CENTRAL_BOOTSTRAP_FILE = "/home/sysadmin/localhost.yml"

# Fields to copy from central cloud bootstrap to subcloud bootstrap
REGISTRY_FIELDS: List[str] = ["docker_registries", "docker_no_proxy", "ssl_ca_cert"]


# --- Setup Helpers ---


def get_undeployed_subcloud_name() -> str:
    """Get an undeployed subcloud name, checking both system controllers.

    Returns:
        str: Subcloud name ready for deployment.
    """
    subcloud_name = SubcloudPickerKeywords.pick_undeployed_with_fallback()
    if subcloud_name is not None:
        return subcloud_name

    get_logger().log_info("All config subclouds are deployed, removing one to free it")
    owner_ssh, result = pick_subcloud_with_fallback(present_in_config=True)
    subcloud_name = result.get_name()
    DcManagerSubcloudLifecycleKeywords(owner_ssh).delete_subcloud(subcloud_name)
    return subcloud_name


# --- Orchestrator ---


def deploy_subcloud_phased_with_registry_routes(ssh_connection: SSHConnection, subcloud_name: str, release_id: str = None) -> None:
    """Deploy a subcloud using phased deploy with external registry route injection.

    Performs: create -> install -> add route -> verify ping -> bootstrap -> config.
    Discovers the NAT64 route from the system controller and replicates it on
    the subcloud with the subcloud's own OAM gateway and interface.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Subcloud to deploy.
        release_id (str): Optional release ID for N-1/N-2 deployments.
    """
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_config = lab_config.get_subcloud(subcloud_name)
    subcloud_oam_ip = subcloud_config.get_first_controller().get_ip()
    password = subcloud_config.get_admin_credentials().get_password()

    bootstrap_values_kw = BootstrapValuesKeywords(ssh_connection)
    ip_route_kw = IPRouteKeywords(ssh_connection)

    external_registry = bootstrap_values_kw.get_external_registry_from_bootstrap(subcloud_name)
    if not external_registry:
        get_logger().log_info(f"No external registry in bootstrap values for '{subcloud_name}', skipping route injection")
    else:
        get_logger().log_info(f"External registry detected: {external_registry}")

    if release_id:
        get_logger().log_info(f"Target release: {release_id}")

    dcm_sc_deploy_kw = DCManagerSubcloudDeployKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Create subcloud '{subcloud_name}'")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_create(subcloud_name, release_id=release_id)

    get_logger().log_test_case_step(f"Install subcloud '{subcloud_name}'")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_install(subcloud_name, release_id=release_id)

    if external_registry:
        registry_ip = ip_route_kw.resolve_hostname(external_registry)
        nat64_prefix, gateway_suffix = ip_route_kw.get_nat64_route_details(registry_ip)
        oam_interface = bootstrap_values_kw.get_oam_interface_from_install_values(subcloud_name)
        oam_gateway = IPRouteKeywords.build_nat64_gateway(subcloud_oam_ip, gateway_suffix)
        get_logger().log_info(f"Subcloud: {subcloud_name}, OAM IP: {subcloud_oam_ip}, NAT64 prefix: {nat64_prefix}, GW: {oam_gateway}, IF: {oam_interface}")

        get_logger().log_test_case_step(f"SSH to subcloud '{subcloud_name}' and add IPv6 route to external registry")
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        subcloud_route_kw = IPRouteKeywords(subcloud_ssh)
        subcloud_route_kw.add_ipv6_route(nat64_prefix, oam_gateway, oam_interface, subcloud_oam_ip, password)

        get_logger().log_test_case_step(f"Verify connectivity to external registry from subcloud '{subcloud_name}'")
        subcloud_route_kw.verify_connectivity_with_retry(registry_ip, f"Ping to external registry '{registry_ip}' from subcloud")

    get_logger().log_test_case_step(f"Bootstrap subcloud '{subcloud_name}'")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_bootstrap(subcloud_name)

    get_logger().log_test_case_step(f"Configure subcloud '{subcloud_name}'")
    dcm_sc_deploy_kw.dcmanager_subcloud_deploy_config(subcloud_name)


# --- Teardown Helpers ---


def cleanup_subcloud_bootstrap(ssh_connection: SSHConnection, backup_file: str, original_file: str) -> None:
    """Restore subcloud bootstrap values from backup.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
        backup_file (str): Path to the backup file.
        original_file (str): Original bootstrap file path.
    """
    get_logger().log_teardown_step("Restore subcloud bootstrap values")
    BootstrapValuesKeywords(ssh_connection).restore_bootstrap_from_backup(backup_file, original_file)


def manage_subcloud(ssh_connection: SSHConnection, subcloud_name: str) -> None:
    """Wait for subcloud to come online and manage it.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Subcloud to manage.
    """
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Wait for subcloud '{subcloud_name}' to come online")
    dcm_sc_list_kw.validate_subcloud_availability_status(subcloud_name)

    get_logger().log_test_case_step(f"Manage subcloud '{subcloud_name}'")
    DcManagerSubcloudManagerKeywords(ssh_connection).get_dcmanager_subcloud_manage(subcloud_name, timeout=60)


# --- Test Cases ---


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_ipv6
def test_deploy_single_subcloud_n_release_with_registry_routes(request: FixtureRequest):
    """Deploy a single subcloud on N release with external registry route injection.

    Performs phased subcloud deployment with NAT64 route injection between
    install and bootstrap. Configures the subcloud's bootstrap values with
    the external registry from the system controller, then deploys.

    Preconditions:
        - System controller is accessible
        - System controller has a working NAT64 route to external registry
        - At least one subcloud is defined in the lab config

    Setup:
        - Sync deployment assets
        - Find or free an undeployed subcloud
        - Backup and inject external registry into subcloud bootstrap values

    Test Steps:
        1. Create subcloud via dcmanager subcloud deploy create
        2. Install subcloud via dcmanager subcloud deploy install
        3. SSH to subcloud and add NAT64 route to external registry
        4. Verify connectivity to external registry
        5. Bootstrap subcloud via dcmanager subcloud deploy bootstrap
        6. Configure subcloud via dcmanager subcloud deploy config
        7. Manage subcloud
        8. Validate subcloud health

    Teardown:
        - Restore original subcloud bootstrap values
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(ssh_connection).sync_assets()

    get_logger().log_setup_step("Find or free an undeployed subcloud")
    subcloud_name = get_undeployed_subcloud_name()

    get_logger().log_setup_step("Backup and inject external registry into subcloud bootstrap values")
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
    subcloud_bootstrap_file = sc_assets.get_bootstrap_file()
    bootstrap_values_kw = BootstrapValuesKeywords(ssh_connection)
    backup_file = bootstrap_values_kw.inject_central_registry_into_bootstrap(subcloud_name, CENTRAL_BOOTSTRAP_FILE, REGISTRY_FIELDS)

    request.addfinalizer(lambda: cleanup_subcloud_bootstrap(ssh_connection, backup_file, subcloud_bootstrap_file))

    deploy_subcloud_phased_with_registry_routes(ssh_connection, subcloud_name)
    manage_subcloud(ssh_connection, subcloud_name)

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' health")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_ipv6
def test_deploy_single_subcloud_n_minus_1_release_with_registry_routes(request: FixtureRequest):
    """Deploy a single subcloud on N-1 release with external registry route injection.

    Preconditions:
        - System controller is accessible
        - System controller has a working NAT64 route to external registry
        - At least one subcloud is defined in the lab config

    Setup:
        - Sync deployment assets
        - Find or free an undeployed subcloud
        - Backup and inject external registry into subcloud bootstrap values

    Test Steps:
        1. Create subcloud via dcmanager subcloud deploy create
        2. Install subcloud via dcmanager subcloud deploy install
        3. SSH to subcloud and add NAT64 route to external registry
        4. Verify connectivity to external registry
        5. Bootstrap subcloud via dcmanager subcloud deploy bootstrap
        6. Configure subcloud via dcmanager subcloud deploy config
        7. Manage subcloud
        8. Validate subcloud health

    Teardown:
        - Restore original subcloud bootstrap values
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(ssh_connection).sync_assets()

    get_logger().log_setup_step("Find or free an undeployed subcloud")
    subcloud_name = get_undeployed_subcloud_name()

    get_logger().log_setup_step("Backup and inject external registry into subcloud bootstrap values")
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
    subcloud_bootstrap_file = sc_assets.get_bootstrap_file()
    bootstrap_values_kw = BootstrapValuesKeywords(ssh_connection)
    backup_file = bootstrap_values_kw.inject_central_registry_into_bootstrap(subcloud_name, CENTRAL_BOOTSTRAP_FILE, REGISTRY_FIELDS)

    request.addfinalizer(lambda: cleanup_subcloud_bootstrap(ssh_connection, backup_file, subcloud_bootstrap_file))

    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    get_logger().log_info(f"Target release: {n_minus_1_release}")

    deploy_subcloud_phased_with_registry_routes(ssh_connection, subcloud_name, release_id=n_minus_1_release)
    manage_subcloud(ssh_connection, subcloud_name)

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' health")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p1
@mark.lab_has_subcloud
@mark.subcloud_lab_is_ipv6
def test_deploy_single_subcloud_n_minus_2_release_with_registry_routes(request: FixtureRequest):
    """Deploy a single subcloud on N-2 release with external registry route injection.

    Preconditions:
        - System controller is accessible
        - System controller has a working NAT64 route to external registry
        - At least one subcloud is defined in the lab config

    Setup:
        - Sync deployment assets
        - Find or free an undeployed subcloud
        - Backup and inject external registry into subcloud bootstrap values

    Test Steps:
        1. Create subcloud via dcmanager subcloud deploy create
        2. Install subcloud via dcmanager subcloud deploy install
        3. SSH to subcloud and add NAT64 route to external registry
        4. Verify connectivity to external registry
        5. Bootstrap subcloud via dcmanager subcloud deploy bootstrap
        6. Configure subcloud via dcmanager subcloud deploy config
        7. Manage subcloud
        8. Validate subcloud health

    Teardown:
        - Restore original subcloud bootstrap values
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Sync deployment assets")
    SyncDeploymentAssets(ssh_connection).sync_assets()

    get_logger().log_setup_step("Find or free an undeployed subcloud")
    subcloud_name = get_undeployed_subcloud_name()

    get_logger().log_setup_step("Backup and inject external registry into subcloud bootstrap values")
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
    subcloud_bootstrap_file = sc_assets.get_bootstrap_file()
    bootstrap_values_kw = BootstrapValuesKeywords(ssh_connection)
    backup_file = bootstrap_values_kw.inject_central_registry_into_bootstrap(subcloud_name, CENTRAL_BOOTSTRAP_FILE, REGISTRY_FIELDS)

    request.addfinalizer(lambda: cleanup_subcloud_bootstrap(ssh_connection, backup_file, subcloud_bootstrap_file))

    n_minus_2_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    get_logger().log_info(f"Target release: {n_minus_2_release}")

    deploy_subcloud_phased_with_registry_routes(ssh_connection, subcloud_name, release_id=n_minus_2_release)
    manage_subcloud(ssh_connection, subcloud_name)

    get_logger().log_test_case_step(f"Validate subcloud '{subcloud_name}' health")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()
