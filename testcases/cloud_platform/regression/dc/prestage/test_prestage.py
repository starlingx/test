from packaging.version import parse
from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_prestage_strategy_keywords import DcmanagerPrestageStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_prestage import DcmanagerSubcloudPrestage
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.metadata.metadata_keywords import MetadataKeywords
from keywords.cloud_platform.dcmanager.rehoming_utils import perform_rehome_operation, verify_subcloud_healthy
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.upgrade.software_deploy_precheck_keywords import SoftwareDeployPrecheckKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.linux.pkill.pkill_keywords import PkillKeywords


def upload_patches(ssh_connection: SSHConnection):
    """Upload patches to system"""
    usm_keywords = USMKeywords(ssh_connection)
    usm_config = ConfigurationManager.get_usm_config()
    patch_file_list = usm_config.get_patch_path()

    release_ids = []
    for patch_file_path in patch_file_list:
        upload_patch_out = usm_keywords.upload_patch_file(patch_file_path, os_region_name="SystemController")
        upload_patch_obj = upload_patch_out.get_software_uploaded()
        if not upload_patch_obj:
            raise Exception(f"Failed to upload patch file: {patch_file_path}")
        uploaded_file = upload_patch_obj[0].get_uploaded_file()
        release = upload_patch_obj[0].get_release()
        get_logger().log_info(f"Uploaded patch file: {uploaded_file} with release ID: {release}")
        release_ids.append(release)
    return release_ids


def deploy_host_and_swact(ssh_connection: SSHConnection, hostname: str):
    """Do software deploy host on all hosts"""
    usm_keywords = USMKeywords(ssh_connection)
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()
    standby_controller = SystemHostListKeywords(ssh_connection).get_standby_controller()

    if SystemHostLockKeywords(ssh_connection).is_host_unlocked(hostname):
        SystemHostLockKeywords(ssh_connection).lock_host(hostname)
    usm_keywords.software_deploy_host(hostname)
    SystemHostLockKeywords(ssh_connection).unlock_host(hostname)
    SystemHostSwactKeywords(ssh_connection).host_swact()
    SystemHostSwactKeywords(ssh_connection).wait_for_swact(active_controller, standby_controller)


def apply_patches(ssh_connection: SSHConnection, release_ids: list[str]):
    """Apply patches on system"""
    usm_keywords = USMKeywords(ssh_connection)
    for release_id in release_ids:
        SoftwareDeployPrecheckKeywords(ssh_connection).deploy_precheck(release_id)
        usm_keywords.deploy_start(release_id)
        usm_keywords.wait_for_deploy_state("deploy-start-done")

        upgrade_order = usm_keywords.deploy_host_upgrade_order()
        for host in upgrade_order:
            deploy_host_and_swact(ssh_connection, host)

        usm_keywords.wait_for_deploy_state("deploy-host-done")
        usm_keywords.wait_for_deploy_host_list_state("deploy-host-deployed")
        usm_keywords.software_deploy_activate()
        usm_keywords.wait_for_deploy_state("deploy-activate-done")
        usm_keywords.software_deploy_complete()
        usm_keywords.software_deploy_delete()
        SoftwareListKeywords(ssh_connection).get_software_list().wait_for_release_state(release_id, "deployed")


def subcloud_rehome(subcloud_name: str, origin_ssh: SSHConnection, destination_ssh: SSHConnection):
    """Rehome subcloud"""
    # Gets the subcloud bootstrap and install values files
    get_logger().log_info(f"Getting deployment assets for subcloud {subcloud_name}")
    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    subcloud_bootstrap_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_bootstrap_file()
    subcloud_install_values = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_install_file()

    get_logger().log_info(f"Rehoming subcloud {subcloud_name} to {destination_ssh}")
    perform_rehome_operation(origin_ssh, destination_ssh, subcloud_name, subcloud_bootstrap_values, subcloud_install_values, sync_assets=False)

    # Validations after rehome operation
    get_logger().log_info(f"Validating subcloud {subcloud_name} is healthy after rehome attempt")
    verify_subcloud_healthy(destination_ssh, subcloud_name, check_sync=False)


def subcloud_upgrade(central_ssh, subcloud_name):
    """Upgrade subcloud"""
    # delete existing prestage strategy
    DcmanagerPrestageStrategyKeywords(central_ssh).get_dcmanager_prestage_strategy_delete()
    # Attempt sw-deploy-strategy delete to prevent sw-deploy-strategy create failure.
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_delete()

    sw_release = SoftwareListKeywords(central_ssh).get_software_list().get_release_name_by_state("deployed")
    latest_deployed_release = max(sw_release)
    # Create software deploy strategy
    get_logger().log_info(f"Create sw-deploy strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_create(subcloud_name=subcloud_name, release=latest_deployed_release, with_delete=True)

    # Apply the previously created strategy
    get_logger().log_info(f"Apply strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_apply(target=subcloud_name)

    strategy_status = DcmanagerStrategyStepKeywords(central_ssh).get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show().get_state()

    # Verify that the strategy was applied correctly
    validate_equals(strategy_status, "complete", f"Software deploy completed successfully for subcloud {subcloud_name}.")


def prestage_subcloud(central_ssh, subcloud_name, subcloud_password, release: str = None, for_sw_deploy: bool = False, kill_proccess: bool = False, expect_fail: bool = False):
    """Prestage subcloud"""

    get_logger().log_info(f"Subcloud selected for prestage: {subcloud_name} (release={release}, for_sw_deploy={for_sw_deploy}, expect_fail={expect_fail})")
    wait_completion = not kill_proccess
    DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name, subcloud_password, release=release, for_sw_deploy=for_sw_deploy, wait_completion=wait_completion)
    if expect_fail:
        prestage_result = "failed"
        success_msg = f"subcloud {subcloud_name} prestage failed."
        if kill_proccess:
            # kill prestage playbook
            prestage_playbook = "/usr/share/ansible/stx-ansible/playbooks/prestage_sw_packages.yml"
            PkillKeywords(central_ssh).pkill_by_pattern(prestage_playbook, send_as_sudo=True)
    else:
        prestage_result = "complete"
        success_msg = f"subcloud {subcloud_name} prestage success."

    obj_subcloud = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    validate_equals(obj_subcloud.get_prestage_status(), prestage_result, success_msg)


@mark.p0
@mark.lab_has_subcloud
def test_subcloud_prestage():
    """Test the prestage of a subcloud."""
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    sc_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(sc_name)
    SystemHostSwactKeywords(subcloud_ssh).ensure_duplex_subcloud_c0_is_active(sc_name)

    # validate Healthy status
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

    # Gets the lowest subcloud sysadmin password
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(sc_name)
    syspass = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(ssh_connection, sc_name, syspass)

    # validate Healthy status
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p0
@mark.lab_has_subcloud
def test_major_release_prestage_retry_after_fail():
    """Verify major release prestage retry after fail and do subcloud upgrade

    Test Steps:
        - Verify subcloud health
        - Prestage subcloud
        - Kill prestage playbook to make prestage fail
        - Retry prestage
        - Upgrade subcloud after prestage complete
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()
    get_logger().log_info(f"Subcloud release {last_major_release}")

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    if subcloud_sw_version != last_major_release:
        fail(f"{subcloud_name} in running {subcloud_sw_version} version, should be {last_major_release}.")

    # Prechecks Before Prestage
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for prestage, backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True, kill_proccess=True, expect_fail=True)

    # Retry prestage subcloud
    prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)

    subcloud_upgrade(central_ssh, subcloud_name)

    # validate Healthy status
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p0
@mark.lab_has_subcloud
def test_minor_release_prestage_retry_after_fail():
    """Verify minor release prestage retry after fail and do subcloud upgrade

    Test Steps:
        - Verify subcloud health
        - Prestage subcloud
        - Kill prestage playbook to make prestage fail
        - Retry prestage
        - Upgrade subcloud after prestage complete
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    if not (latest_deployed_release_with_patch := SoftwareListKeywords(central_ssh).get_software_list().system_has_patch()):
        fail(f"Controller is running version {latest_deployed_release_with_patch}, does not have a patch.")
    latest_deployed_release = max(SoftwareListKeywords(central_ssh).get_software_list().get_product_version_by_state("deployed"))
    get_logger().log_info(f"Subcloud release {latest_deployed_release_with_patch}")

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    if subcloud_sw_version != latest_deployed_release:
        fail(f"{subcloud_name} is running {subcloud_sw_version} version, should be {latest_deployed_release}.")

    # Prechecks Before Prestage
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True, kill_proccess=True, expect_fail=True)

    # Retry prestage subcloud
    prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)

    subcloud_upgrade(central_ssh, subcloud_name)

    # validate Healthy status
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p0
@mark.lab_has_subcloud
def test_prestage_for_multiple_deployment_states(request):
    """Verify prestage for multiple release deployment states

    Test Steps:
        - Verify subcloud health
        - Prestage subcloud with N release
        - Simulate release in state "deploying"
        - Verify that prestage for N release fails
        - Simulate release in state "removing"
        - Verify that prestage for N-1 release fails
        - Simulate release in state "unavailable"
        - Verify that prestage for N release succeeds
        - Simulate release in state "deployed"
        - Verify that prestage for N release succeeds
        - Simulate release in state "committed"
        - Verify that prestage for N release succeeds
        - Simulate release in state "available"
        - Verify that prestage succeeds
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    central_sw_version = max(SoftwareListKeywords(central_ssh).get_software_list().get_product_version_by_state("deployed"))

    # Select subcloud from config file to ensure parallel execution safety.
    # Each config file is scoped to specific subclouds, preventing runners from
    # operating on each other's subclouds during parallel execution.
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    get_logger().log_info(f"Central cloud version: {central_sw_version}, Subcloud {subcloud_name} version: {subcloud_sw_version}")

    # Prechecks Before Prestage
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Log software list from subcloud before prestage
    subcloud_software_list = SoftwareListKeywords(subcloud_ssh).get_software_list()
    get_logger().log_info(f"Subcloud {subcloud_name} software list: {subcloud_software_list}")

    # Check if there is already a release in "available" state on the subcloud.
    # If not, create a fake one by copying metadata from a deployed release.
    available_releases = SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_name_by_state("available")
    if available_releases:
        sw_release = max(available_releases)
        fake_release_created = False
    else:
        # No release in available state — create a fake one from the deployed release metadata
        deployed_release = max(SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_name_by_state("deployed"))
        fake_release = f"{deployed_release}-fake"
        MetadataKeywords(subcloud_ssh).create_fake_release_metadata(deployed_release, fake_release, source_state="deployed", target_state="available")
        sw_release = fake_release
        fake_release_created = True

    get_logger().log_info(f"Release available {sw_release}.")
    release_metadata = f"/opt/software/metadata/available/{sw_release}-metadata.xml"
    # Use a list to track current metadata location so teardown always sees the latest value
    metadata_location = [release_metadata]
    if FileKeywords(subcloud_ssh).file_exists(release_metadata):

        def teardown():
            current_metadata = metadata_location[0]
            if FileKeywords(subcloud_ssh).file_exists(current_metadata):
                if fake_release_created:
                    FileKeywords(subcloud_ssh).delete_file(current_metadata)
                else:
                    FileKeywords(subcloud_ssh).copy_file(current_metadata, f"/opt/software/metadata/available/{sw_release}-metadata.xml", sudo=True)

        request.addfinalizer(teardown)

        get_logger().log_test_case_step("Scenario 1: Prestage with release in 'deploying' state — expect failure")
        get_logger().log_info(f"Subcloud software list: {SoftwareListKeywords(subcloud_ssh).get_software_list()}")
        FileKeywords(subcloud_ssh).create_directory_with_sudo("/opt/software/metadata/deploying")
        FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/deploying/", sudo=True)
        release_metadata = f"/opt/software/metadata/deploying/{sw_release}-metadata.xml"
        metadata_location[0] = release_metadata
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True, expect_fail=True)
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password, expect_fail=True)

        get_logger().log_test_case_step("Scenario 2: Prestage with release in 'removing' state — expect failure")
        get_logger().log_info(f"Subcloud software list: {SoftwareListKeywords(subcloud_ssh).get_software_list()}")
        FileKeywords(subcloud_ssh).create_directory_with_sudo("/opt/software/metadata/removing")
        FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/removing/", sudo=True)
        release_metadata = f"/opt/software/metadata/removing/{sw_release}-metadata.xml"
        metadata_location[0] = release_metadata
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password, release=subcloud_sw_version, for_sw_deploy=True, expect_fail=True)
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password, release=subcloud_sw_version, expect_fail=True)

        get_logger().log_test_case_step("Scenario 3: Prestage with release in 'unavailable' state — expect success")
        get_logger().log_info(f"Subcloud software list: {SoftwareListKeywords(subcloud_ssh).get_software_list()}")
        FileKeywords(subcloud_ssh).create_directory_with_sudo("/opt/software/metadata/unavailable")
        FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/unavailable/", sudo=True)
        release_metadata = f"/opt/software/metadata/unavailable/{sw_release}-metadata.xml"
        metadata_location[0] = release_metadata
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password)

        get_logger().log_test_case_step("Scenario 4: Prestage with release in 'deployed' state — expect success")
        get_logger().log_info(f"Subcloud software list: {SoftwareListKeywords(subcloud_ssh).get_software_list()}")
        FileKeywords(subcloud_ssh).create_directory_with_sudo("/opt/software/metadata/deployed")
        FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/deployed/", sudo=True)
        release_metadata = f"/opt/software/metadata/deployed/{sw_release}-metadata.xml"
        metadata_location[0] = release_metadata
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password)

        get_logger().log_test_case_step("Scenario 5: Prestage with release in 'committed' state — expect success")
        get_logger().log_info(f"Subcloud software list: {SoftwareListKeywords(subcloud_ssh).get_software_list()}")
        FileKeywords(subcloud_ssh).create_directory_with_sudo("/opt/software/metadata/committed")
        FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/committed/", sudo=True)
        release_metadata = f"/opt/software/metadata/committed/{sw_release}-metadata.xml"
        metadata_location[0] = release_metadata
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password)

        get_logger().log_test_case_step("Scenario 6: Prestage with release back in 'available' state — expect success")
        get_logger().log_info(f"Subcloud software list: {SoftwareListKeywords(subcloud_ssh).get_software_list()}")
        FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/available/", sudo=True)
        release_metadata = f"/opt/software/metadata/available/{sw_release}-metadata.xml"
        metadata_location[0] = release_metadata
        get_logger().log_info("Prestage with for_sw_deploy=False")
        prestage_subcloud(central_ssh, subcloud_name, subcloud_password)


@mark.p0
@mark.lab_has_subcloud
@mark.lab_has_secondary_system_controller
def test_subcloud_with_higher_patch_is_patchable_after_rehoming(request):
    """Verify

    Test Steps:
        - Verify subcloud health
        -
    """
    origin_system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    if not (origin_release := SoftwareListKeywords(origin_system_controller_ssh).get_software_list().system_has_patch()):
        fail(f"Controller is running version {origin_release}, does not have a patch.")

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = max(SoftwareListKeywords(subcloud_ssh).get_software_list().get_product_version_with_patch_by_state("deployed"))

    if subcloud_sw_version != origin_release:
        fail(f"{subcloud_name} is running {subcloud_sw_version} version, should be {origin_release}.")

    destination_system_controller_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()
    if not (destination_release := SoftwareListKeywords(destination_system_controller_ssh).get_software_list().system_has_patch()):
        fail(f"Secondary Controller is running version {destination_release}, does not have a patch.")

    if parse(origin_release) < parse(destination_release):
        fail(f"Secondary Controller should be running a lower version than Primary's Controller {origin_release}. Currently running {destination_release}")

    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    release_id_list = upload_patches(destination_system_controller_ssh)
    apply_patches(destination_system_controller_ssh, release_id_list)

    prestage_subcloud(destination_system_controller_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)

    subcloud_upgrade(destination_system_controller_ssh, subcloud_name)


@mark.p0
@mark.lab_has_subcloud
@mark.lab_has_secondary_system_controller
def test_subcloud_with_lower_patch_is_patchable_after_rehoming(request):
    """Verify

    Test Steps:
        - Verify subcloud health
        -
    """
    origin_system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    if not (origin_release := SoftwareListKeywords(origin_system_controller_ssh).get_software_list().system_has_patch()):
        fail(f"Controller is running version {origin_release}, does not have a patch.")

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = max(SoftwareListKeywords(subcloud_ssh).get_software_list().get_product_version_with_patch_by_state("deployed"))

    if subcloud_sw_version != origin_release:
        fail(f"{subcloud_name} is running {subcloud_sw_version} version, should be {origin_release}.")

    destination_system_controller_ssh = LabConnectionKeywords().get_secondary_active_controller_ssh()
    if not (destination_release := SoftwareListKeywords(destination_system_controller_ssh).get_software_list().system_has_patch()):
        fail(f"Secondary Controller is running version {destination_release}, does not have a patch.")

    if parse(origin_release) > parse(destination_release):
        fail(f"Secondary Controller should be running a higher version than Primary's Controller {origin_release}. Currently running {destination_release}")

    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(destination_system_controller_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)

    subcloud_upgrade(destination_system_controller_ssh, subcloud_name)
