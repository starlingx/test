from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_prestage import DcmanagerSubcloudPrestage
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.fm_client_cli_keywords import FaultManagementClientCLIKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.object.fm_client_cli_object import FaultManagementClientCLIObject
from keywords.cloud_platform.metadata.metadata_keywords import MetadataKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.linux.pkill.pkill_keywords import PkillKeywords


# --- Helper Functions ---


def ensure_subcloud_managed(ssh_connection: SSHConnection, subcloud_name: str) -> None:
    """Ensure subcloud is managed before operations.

    Args:
        ssh_connection (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud.
    """
    subcloud = DcManagerSubcloudListKeywords(ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    if subcloud.get_management() == "unmanaged":
        get_logger().log_info(f"Subcloud {subcloud_name} is unmanaged, managing it before prestage")
        DcManagerSubcloudManagerKeywords(ssh_connection).get_dcmanager_subcloud_manage(subcloud_name, 30)


def prestage_subcloud(central_ssh: SSHConnection, subcloud_name: str, subcloud_password: str, release: str = None, for_sw_deploy: bool = False, force: bool = False, kill_process: bool = False, expect_fail: bool = False) -> None:
    """Prestage a subcloud.

    Args:
        central_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud.
        subcloud_password (str): Sysadmin password for the subcloud.
        release (str): Release version to prestage.
        for_sw_deploy (bool): Use --for-sw-deploy flag.
        force (bool): Use --force flag (bypasses alarm checks).
        kill_process (bool): Kill the prestage playbook to simulate failure.
        expect_fail (bool): Whether the prestage is expected to fail.
    """
    get_logger().log_info(f"Prestage subcloud: {subcloud_name} (release={release}, for_sw_deploy={for_sw_deploy}, force={force}, expect_fail={expect_fail})")
    wait_completion = not kill_process
    DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name, subcloud_password, release=release, for_sw_deploy=for_sw_deploy, force=force, wait_completion=wait_completion)

    if kill_process:
        prestage_playbook = "/usr/share/ansible/stx-ansible/playbooks/prestage_sw_packages.yml"
        PkillKeywords(central_ssh).pkill_by_pattern(prestage_playbook, send_as_sudo=True)

    if expect_fail:
        prestage_result = "failed"
        success_msg = f"Subcloud {subcloud_name} prestage failed as expected."
    else:
        prestage_result = "complete"
        success_msg = f"Subcloud {subcloud_name} prestage completed successfully."

    obj_subcloud = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    validate_equals(obj_subcloud.get_prestage_status(), prestage_result, success_msg)


# --- Prestage for Install ---


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_install_n_release(request):
    """Verify prestage for-install with N release (default).

    Test Steps:
        1. Prestage subcloud (for-install, no --release arg)
        2. Validate prestage status is complete

    Teardown:
        - None
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password)


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_install_n_minus_1_release(request):
    """Verify prestage for-install with N-1 release (--release N-1).

    Requires that the N-1 release ISO is available on the system controller.

    Test Steps:
        1. Resolve N-1 release version
        2. Prestage subcloud with --release N-1
        3. Validate prestage status is complete

    Teardown:
        - None
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    get_logger().log_info(f"Prestaging subcloud {subcloud_name} for install with release {n_minus_1_release}")

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=n_minus_1_release)


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_install_retry_after_process_kill_n_release(request):
    """Verify prestage for-install N release retry after process kill.

    Test Steps:
        1. Prestage subcloud (for-install)
        2. Kill prestage playbook to simulate failure
        3. Validate prestage status is failed
        4. Retry prestage (for-install)
        5. Validate prestage status is complete

    Teardown:
        - None
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, kill_process=True, expect_fail=True)
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password)


# --- Prestage for SW Deploy ---


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_sw_deploy_retry_after_process_kill_n_minus_1_release(request):
    """Verify prestage --for-sw-deploy with N-1 release retry after process kill.

    Requires that the N-1 release is available on the system controller.

    Test Steps:
        1. Resolve N-1 release version
        2. Prestage subcloud with --for-sw-deploy --release N-1
        3. Kill prestage playbook to simulate failure
        4. Validate prestage status is failed
        5. Retry prestage with --for-sw-deploy --release N-1
        6. Validate prestage status is complete

    Teardown:
        - None
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    n_minus_1_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=n_minus_1_release, for_sw_deploy=True, kill_process=True, expect_fail=True)
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=n_minus_1_release, for_sw_deploy=True)


# --- Prestage Scenario Tests ---


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_multiple_deployment_states(request):
    """Verify prestage behavior across different release deployment states.

    Tests that prestage correctly succeeds or fails depending on the state
    of the release metadata on the subcloud (deploying, removing, unavailable,
    deployed, committed, available).

    Test Steps:
        1. Prestage with release in 'deploying' state - expect failure
        2. Prestage with release in 'removing' state - expect failure
        3. Prestage with release in 'unavailable' state - expect success
        4. Prestage with release in 'deployed' state - expect success
        5. Prestage with release in 'committed' state - expect success
        6. Prestage with release back in 'available' state - expect success

    Teardown:
        - Restore release metadata to original location
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_sw_version = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Check if there is already a release in "available" state on the subcloud
    available_releases = SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_name_by_state("available")
    if available_releases:
        sw_release = max(available_releases)
        fake_release_created = False
    else:
        deployed_release = max(SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_name_by_state("deployed"))
        fake_release = f"{deployed_release}-fake"
        MetadataKeywords(subcloud_ssh).create_fake_release_metadata(deployed_release, fake_release, source_state="deployed", target_state="available")
        sw_release = fake_release
        fake_release_created = True

    get_logger().log_info(f"Release available: {sw_release}")
    release_metadata = f"/opt/software/metadata/available/{sw_release}-metadata.xml"
    metadata_location = [release_metadata]

    if not FileKeywords(subcloud_ssh).file_exists(release_metadata):
        fail(f"Release metadata file {release_metadata} does not exist on subcloud")

    def teardown():
        current_metadata = metadata_location[0]
        if FileKeywords(subcloud_ssh).file_exists(current_metadata):
            if fake_release_created:
                FileKeywords(subcloud_ssh).delete_file(current_metadata)
            else:
                FileKeywords(subcloud_ssh).copy_file(current_metadata, f"/opt/software/metadata/available/{sw_release}-metadata.xml", sudo=True)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Scenario 1: Prestage with release in 'deploying' state - expect failure")
    get_logger().log_info(f"Subcloud software list: {SoftwareListKeywords(subcloud_ssh).get_software_list()}")
    FileKeywords(subcloud_ssh).create_directory_with_sudo("/opt/software/metadata/deploying")
    FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/deploying/", sudo=True)
    release_metadata = f"/opt/software/metadata/deploying/{sw_release}-metadata.xml"
    metadata_location[0] = release_metadata
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, for_sw_deploy=True, expect_fail=True)
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, expect_fail=True)

    get_logger().log_test_case_step("Scenario 2: Prestage with release in 'removing' state - expect failure")
    FileKeywords(subcloud_ssh).create_directory_with_sudo("/opt/software/metadata/removing")
    FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/removing/", sudo=True)
    release_metadata = f"/opt/software/metadata/removing/{sw_release}-metadata.xml"
    metadata_location[0] = release_metadata
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=subcloud_sw_version, for_sw_deploy=True, expect_fail=True)
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=subcloud_sw_version, expect_fail=True)

    get_logger().log_test_case_step("Scenario 3: Prestage with release in 'unavailable' state - expect success")
    FileKeywords(subcloud_ssh).create_directory_with_sudo("/opt/software/metadata/unavailable")
    FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/unavailable/", sudo=True)
    release_metadata = f"/opt/software/metadata/unavailable/{sw_release}-metadata.xml"
    metadata_location[0] = release_metadata
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password)

    get_logger().log_test_case_step("Scenario 4: Prestage with release in 'deployed' state - expect success")
    FileKeywords(subcloud_ssh).create_directory_with_sudo("/opt/software/metadata/deployed")
    FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/deployed/", sudo=True)
    release_metadata = f"/opt/software/metadata/deployed/{sw_release}-metadata.xml"
    metadata_location[0] = release_metadata
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password)

    get_logger().log_test_case_step("Scenario 5: Prestage with release in 'committed' state - expect success")
    FileKeywords(subcloud_ssh).create_directory_with_sudo("/opt/software/metadata/committed")
    FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/committed/", sudo=True)
    release_metadata = f"/opt/software/metadata/committed/{sw_release}-metadata.xml"
    metadata_location[0] = release_metadata
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password)

    get_logger().log_test_case_step("Scenario 6: Prestage with release back in 'available' state - expect success")
    FileKeywords(subcloud_ssh).move_file(source=release_metadata, destination="/opt/software/metadata/available/", sudo=True)
    release_metadata = f"/opt/software/metadata/available/{sw_release}-metadata.xml"
    metadata_location[0] = release_metadata
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password)


# --- Negative Tests ---


@mark.p2
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_fails_with_mgmt_alarm_but_succeeds_with_force(request):
    """Verify prestage fails with management alarm and succeeds with --force.

    Test Steps:
        1. Inject a management affecting alarm on the subcloud
        2. Attempt prestage --for-sw-deploy (expect failure due to alarm)
        3. Retry prestage with --force flag (expect success despite alarm)

    Teardown:
        - Clear injected alarm if still present
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    # Prepare alarm injection
    fm_client_cli_keywords = FaultManagementClientCLIKeywords(subcloud_ssh)
    fm_client_cli_object = FaultManagementClientCLIObject()
    fm_client_cli_object.set_alarm_id(FaultManagementClientCLIObject.DEFAULT_ALARM_ID)
    fm_client_cli_object.set_entity_id(f"name={subcloud_name}")

    def teardown():
        alarm_list = AlarmListKeywords(subcloud_ssh).alarm_list()
        if any(alarm.alarm_id == fm_client_cli_object.get_alarm_id() for alarm in alarm_list):
            get_logger().log_info(f"Teardown: Clearing injected alarm from subcloud {subcloud_name}")
            fm_client_cli_keywords.delete_alarm(fm_client_cli_object)

    request.addfinalizer(teardown)

    # Inject management affecting alarm
    get_logger().log_info(f"Injecting management affecting alarm on subcloud {subcloud_name}")
    fm_client_cli_keywords.raise_alarm(fm_client_cli_object)

    # Attempt prestage - expect failure due to alarm
    get_logger().log_info(f"Attempting prestage of {subcloud_name} (expecting failure due to alarm)")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, for_sw_deploy=True, expect_fail=True)

    # Retry prestage with --force - expect success despite alarm
    get_logger().log_info(f"Retrying prestage of {subcloud_name} with --force flag")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, for_sw_deploy=True, force=True)
