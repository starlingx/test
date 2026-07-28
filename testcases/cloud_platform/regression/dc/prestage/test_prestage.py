import re
from pytest import fail, mark

from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_greater_than_or_equal, validate_list_contains, validate_none, validate_not_none
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
from keywords.cloud_platform.postgresql.postgresql_keywords import PostgresqlKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
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


def teardown_clear_prestage_data(central_ssh: SSHConnection, subcloud_name: str, *releases: str) -> None:
    """Clear prestage_versions/prestage_status and remove release metadata created during prestage.

    Runs: sudo -u postgres psql -d dcmanager -c "update subclouds set
    prestage_versions=null, prestage_status=null where name='<subcloud_name>'"

    Also removes any release metadata xml file left behind on the subcloud
    under /opt/software/metadata/available/ (e.g.
    /opt/software/metadata/available/starlingx-26.10.1-metadata.xml or
    /opt/software/metadata/available/WRCP-26.10.1-metadata.xml) for the
    releases used during the test's prestage calls.

    Args:
        central_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud to clear prestage data for.
        *releases (str): Release versions used during the test's prestage
            calls (e.g. "26.10"). Any metadata file whose name contains
            '<release>' is removed, regardless of prefix (starlingx-, WRCP-, etc).
    """
    metadata_dir = "/opt/software/metadata/available/"
    if releases:
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        file_keywords = FileKeywords(subcloud_ssh)
        metadata_files = file_keywords.get_files_in_dir(metadata_dir, is_sudo=True)
        for release in releases:
            matching_files = [metadata_file for metadata_file in metadata_files if release in metadata_file]
            for metadata_file in matching_files:
                file_keywords.delete_file(f"{metadata_dir}{metadata_file}")

    query = f"update subclouds set prestage_versions=null, prestage_status=null where name='{subcloud_name}'"
    PostgresqlKeywords(central_ssh).query_database("dcmanager", query)


def prestage_subcloud(central_ssh: SSHConnection, subcloud_name: str, subcloud_password: str, release: str = None, for_sw_deploy: bool = False, for_install: bool = False, force: bool = False, kill_process: bool = False, expect_fail: bool = False, expect_rejection: bool = False) -> str:
    """Prestage a subcloud.

    Args:
        central_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud.
        subcloud_password (str): Sysadmin password for the subcloud.
        release (str): Release version to prestage.
        for_sw_deploy (bool): Use --for-sw-deploy flag.
        for_install (bool): Use --for-install flag.
        force (bool): Use --force flag (bypasses alarm checks).
        kill_process (bool): Kill the prestage playbook to simulate failure.
        expect_fail (bool): Whether the prestage is expected to fail asynchronously
            (command accepted with rc=0 but prestage_status reaches "failed").
        expect_rejection (bool): Whether the prestage command is expected to be
            rejected immediately (rc=1, e.g. alarm check or already prestaging).

    Returns:
        str: Error output from the CLI when expect_rejection is True, empty string otherwise.
    """
    get_logger().log_info(f"Prestage subcloud: {subcloud_name} (release={release}, for_sw_deploy={for_sw_deploy}, force={force}, expect_fail={expect_fail}, expect_rejection={expect_rejection})")
    prestage_kw = DcmanagerSubcloudPrestage(central_ssh)

    if for_install and for_sw_deploy:
            fail("--for-sw-deploy and --for-install cannot be combined.")

    if expect_rejection:
        # Command rejected immediately (rc=1) — capture error output, no wait needed
        error_output = prestage_kw.dcmanager_subcloud_prestage_with_error(subcloud_name, subcloud_password, release=release, for_sw_deploy=for_sw_deploy, force=force)
        get_logger().log_info(f"Prestage rejected as expected. Output: {error_output}")
        return error_output

    if expect_fail and not kill_process:
        # Command accepted (rc=0) but prestage fails asynchronously
        prestage_kw.dcmanager_subcloud_prestage(subcloud_name, subcloud_password, release=release, for_sw_deploy=for_sw_deploy, force=force, wait_completion=False)
        prestage_kw.wait_for_prestage(subcloud=subcloud_name, expected_end_state="failed")
        obj_subcloud = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
        validate_equals(obj_subcloud.get_prestage_status(), "failed", f"Subcloud {subcloud_name} prestage failed as expected")
        return ""

    wait_completion = not kill_process

    if for_sw_deploy:
        prestage_kw.dcmanager_subcloud_prestage(subcloud_name, subcloud_password, release=release, for_sw_deploy=for_sw_deploy, force=force, wait_completion=wait_completion)
    elif for_install:
        prestage_kw.dcmanager_subcloud_prestage(subcloud_name, subcloud_password, release=release, for_install=for_install, force=force, wait_completion=wait_completion)
    else:
        fail("Unknown operation.")

    if kill_process:
        prestage_playbook = "/usr/share/ansible/stx-ansible/playbooks/prestage_sw_packages.yml"
        PkillKeywords(central_ssh).pkill_by_pattern(prestage_playbook, send_as_sudo=True)
        prestage_kw.wait_for_prestage(subcloud=subcloud_name, expected_end_state="failed")
        obj_subcloud = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
        validate_equals(obj_subcloud.get_prestage_status(), "failed", f"Subcloud {subcloud_name} prestage failed as expected")
        return ""

    obj_subcloud = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    validate_equals(obj_subcloud.get_prestage_status(), "complete", f"Subcloud {subcloud_name} prestage completed successfully")
    return ""


# --- Base Test ---


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
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)
    prestage_release = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=prestage_release, for_install=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_install_versions = for_install.split(",")
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(prestage_release, for_install_versions, "Validate that the subcloud was prestaged to the target version.")

    prestage_files_path = f"/opt/platform-backup/{prestage_release}"
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/local_registry_filesystem.tgz"), True, f"local_registry_filesystem.tgz exists in {prestage_files_path}")
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/ostree_repo"), True, f"ostree_repo exists in {prestage_files_path}")


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_sw_deploy_n_release(request):
    """Verify prestage for-sw-deploy with N release (default).

    Test Steps:
        1. Prestage subcloud (for-sw-deploy, no --release arg)
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
    prestage_release = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=prestage_release, for_sw_deploy=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_sw_deploy_versions = [re.search(r"(\d+\.\d+)", version).group(1) for version in for_sw_deploy.split(",")]
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(prestage_release, for_sw_deploy_versions, "Validate that the subcloud was prestaged to the target version.")



# --- Prestage for Install ---


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_install_n_release_on_n_release(request):
    """Verify prestage for-install with N release.

    Test Steps:
        1. Resolve N release and matching patch on the system controller
        2. Prestage subcloud with --for-install
        3. Validate prestage_versions for-install matches the target release

    Teardown:
        - Clear prestage_versions and prestage_status from the dcmanager database.
    """
    required_release = str(CloudPlatformVersionManagerClass().get_sw_version())

    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load=required_release,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, required_release))

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=required_release, for_install=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_install_versions = for_install.split(",")
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(required_release, for_install_versions, "Validate that the subcloud was prestaged to the target version.")

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    prestage_files_path = f"/opt/platform-backup/{required_release}"
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/local_registry_filesystem.tgz"), True, f"local_registry_filesystem.tgz exists in {prestage_files_path}")
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/ostree_repo"), True, f"ostree_repo exists in {prestage_files_path}")


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_install_n_minus_one_release(request):
    """Verify prestage for-install with N-1 release.

    Requires that the N-1 release is available on the system controller.

    Test Steps:
        1. Resolve N-1 release and matching patch on the system controller
        2. Prestage subcloud with --for-install --release N-1
        3. Validate prestage_versions for-install matches the target release

    Teardown:
        - Clear prestage_versions and prestage_status from the dcmanager database.
    """
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load=required_release,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, required_release))

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=required_release, for_install=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_install_versions = for_install.split(",")
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(required_release, for_install_versions, "Validate that the subcloud was prestaged to the target version.")

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    prestage_files_path = f"/opt/platform-backup/{required_release}"
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/local_registry_filesystem.tgz"), True, f"local_registry_filesystem.tgz exists in {prestage_files_path}")
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/ostree_repo"), True, f"ostree_repo exists in {prestage_files_path}")


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_install_n_minus_two_release(request):
    """Verify prestage for-install with N-2 release.

    Requires that the N-2 release is available on the system controller.

    Test Steps:
        1. Resolve N-2 release and matching patch on the system controller
        2. Prestage subcloud with --for-install --release N-2
        3. Validate prestage_versions for-install matches the target release

    Teardown:
        - Clear prestage_versions and prestage_status from the dcmanager database.
    """
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())

    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load=required_release,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, required_release))

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=required_release, for_install=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_install_versions = for_install.split(",")
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(required_release, for_install_versions, "Validate that the subcloud was prestaged to the target version.")

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    prestage_files_path = f"/opt/platform-backup/{required_release}"
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/local_registry_filesystem.tgz"), True, f"local_registry_filesystem.tgz exists in {prestage_files_path}")
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/ostree_repo"), True, f"ostree_repo exists in {prestage_files_path}")


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_install_n_release_from_n_minus_two(request):
    """Verify prestage for-install to N release for a subcloud currently running N-2.

    Test Steps:
        1. Select a subcloud currently running the N-2 release
        2. Prestage subcloud with --for-install --release N (reinstall to N)
        3. Validate prestage_versions for-install matches the N release
        4. Validate /opt/platform-backup/<N> has ostree_repo and container image filesystem

    Teardown:
        - Clear prestage_versions and prestage_status from the dcmanager database.
    """
    current_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    target_release = str(CloudPlatformVersionManagerClass().get_sw_version())

    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load=current_release,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, target_release))

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=target_release, for_install=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_install_versions = for_install.split(",")
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(target_release, for_install_versions, "Validate that the subcloud was prestaged to the target version.")

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    prestage_files_path = f"/opt/platform-backup/{target_release}"
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/local_registry_filesystem.tgz"), True, f"local_registry_filesystem.tgz exists in {prestage_files_path}")
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/ostree_repo"), True, f"ostree_repo exists in {prestage_files_path}")


@mark.p0
@mark.lab_has_subcloud
def test_prestage_single_simplex_subcloud_for_install_n_release_from_n_minus_one(request):
    """Verify prestage for-install to N release for a subcloud currently running N-1.

    Test Steps:
        1. Select a subcloud currently running the N-1 release
        2. Prestage subcloud with --for-install --release N (reinstall to N)
        3. Validate prestage_versions for-install matches the N release
        4. Validate /opt/platform-backup/<N> has ostree_repo and container image filesystem

    Teardown:
        - Clear prestage_versions and prestage_status from the dcmanager database.
    """
    current_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    target_release = str(CloudPlatformVersionManagerClass().get_sw_version())

    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load=current_release,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, target_release))

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=target_release, for_install=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_install_versions = for_install.split(",")
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(target_release, for_install_versions, "Validate that the subcloud was prestaged to the target version.")

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    prestage_files_path = f"/opt/platform-backup/{target_release}"
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/local_registry_filesystem.tgz"), True, f"local_registry_filesystem.tgz exists in {prestage_files_path}")
    validate_equals(FileKeywords(subcloud_ssh).file_exists(f"{prestage_files_path}/ostree_repo"), True, f"ostree_repo exists in {prestage_files_path}")


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

@mark.p0
@mark.lab_has_subcloud
def test_verify_prestage_for_sw_deploy_option_n_minus_one_to_n(request):
    """Test verify that when running prestage with option 
    --for-sw-deploy' enabled for an N-1 subcloud, shows N
     release as prestage_version in dcmanager subcloud show
     """
    
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    target_prestage_release = str(CloudPlatformVersionManagerClass().get_sw_version())

    system_controller_ssh, result = pick_subcloud_with_fallback(
    availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
    lab_type=LabTypeEnum.SIMPLEX,
    load=required_release
    )

    subcloud_name = result.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, target_prestage_release))

    software_list = SoftwareListKeywords(system_controller_ssh).get_software_list()
    available_release = software_list.get_release_name_by_state("available") + software_list.get_release_name_by_state("deployed")
    available_release_versions = [re.search(r"(\d+\.\d+)", release).group(1) for release in available_release]
    validate_list_contains(target_prestage_release, available_release_versions, "validate that the system controller has N release available")

    prestage_subcloud(central_ssh=system_controller_ssh, subcloud_name=subcloud_name, subcloud_password=subcloud_password, release=target_prestage_release, for_sw_deploy=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_sw_deploy_versions = [re.search(r"(\d+\.\d+)", version).group(1) for version in for_sw_deploy.split(",")]
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(target_prestage_release, for_sw_deploy_versions, "Validate that for-sw-deploy reflects the N release in prestage_versions.")

    subcloud_software_list = SoftwareListKeywords(subcloud_ssh).get_software_list()
    available_release = software_list.get_release_name_by_state("available") + subcloud_software_list.get_release_name_by_state("available")
    available_release_versions = [re.search(r"(\d+\.\d+)", release).group(1) for release in available_release]
    validate_list_contains(target_prestage_release, available_release_versions, "validate that the subcloud has N release available")


@mark.p0
@mark.lab_has_subcloud
def test_verify_prestage_for_sw_deploy_option_n_minus_two_to_n(request):
    """Test verify that when running prestage with option 
    --for-sw-deploy' enabled for an N-2 subcloud, shows N
     release as prestage_version in dcmanager subcloud show
     """
    
    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    target_prestage_release = str(CloudPlatformVersionManagerClass().get_sw_version())

    system_controller_ssh, result = pick_subcloud_with_fallback(
    availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
    lab_type=LabTypeEnum.SIMPLEX,
    load=required_release
    )

    subcloud_name = result.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, target_prestage_release))

    software_list = SoftwareListKeywords(system_controller_ssh).get_software_list()
    available_release = software_list.get_release_name_by_state("available") + software_list.get_release_name_by_state("deployed")
    available_release_versions = [re.search(r"(\d+\.\d+)", release).group(1) for release in available_release]
    validate_list_contains(target_prestage_release, available_release_versions, "validate that the system controller has N release available")

    prestage_subcloud(central_ssh=system_controller_ssh, subcloud_name=subcloud_name, subcloud_password=subcloud_password, release=target_prestage_release, for_sw_deploy=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_sw_deploy_versions = [re.search(r"(\d+\.\d+)", version).group(1) for version in for_sw_deploy.split(",")]
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(target_prestage_release, for_sw_deploy_versions, "Validate that for-sw-deploy reflects the N release in prestage_versions.")

    subcloud_software_list = SoftwareListKeywords(subcloud_ssh).get_software_list()
    available_release = software_list.get_release_name_by_state("available") + subcloud_software_list.get_release_name_by_state("available")
    available_release_versions = [re.search(r"(\d+\.\d+)", release).group(1) for release in available_release]
    validate_list_contains(target_prestage_release, available_release_versions, "validate that the subcloud has N release available")


@mark.p0
@mark.lab_has_subcloud
def test_verify_prestage_for_sw_deploy_option_n_patching(request):
    """Test verify that when running prestage with option 
        --for-sw-deploy' enabled for an N-2 subcloud, shows N
        release as prestage_version in dcmanager subcloud show
    """

    required_release = str(CloudPlatformVersionManagerClass().get_sw_version())

    system_controller_ssh, result = pick_subcloud_with_fallback(
    availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
    lab_type=LabTypeEnum.SIMPLEX,
    load=required_release
    )

    subcloud_name = result.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, required_release))

    system_controller_patch = SoftwareListKeywords(system_controller_ssh).get_software_list().system_has_patch()
    subcloud_patch = SoftwareListKeywords(subcloud_ssh).get_software_list().system_has_patch()

    validate_not_none(system_controller_patch, "Validate that the system controller has a patch.")
    validate_none(subcloud_patch, "Validate that the subcloud has no patch.")

    system_controller_release_names = SoftwareListKeywords(system_controller_ssh).get_software_list().get_release_name_by_state("deployed")
    matching_release_names = [release_name for release_name in system_controller_release_names if release_name.endswith(system_controller_patch)]
    validate_greater_than_or_equal(len(matching_release_names), 1, f"Validate that a release name matching {system_controller_patch} was found on the system controller. Releases: {system_controller_release_names}")
    target_release_name = matching_release_names[0]

    prestage_subcloud(central_ssh=system_controller_ssh, subcloud_name=subcloud_name, subcloud_password=subcloud_password, for_sw_deploy=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_sw_deploy_versions = for_sw_deploy.split(",")
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(system_controller_patch, for_sw_deploy_versions, "Validate that the subcloud was prestaged to the target version.")

    subcloud_available_releases = SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_name_by_state("available")
    validate_list_contains(target_release_name, subcloud_available_releases, f"Validate that the subcloud software list shows {target_release_name} as available.")

@mark.p0
@mark.lab_has_subcloud
def test_verify_prestage_for_sw_deploy_option_n_minus_one_patching(request):
    """Test verify that when running prestage with option 
        --for-sw-deploy' enabled for an N-1 subcloud, shows N-1
        release as prestage_version in dcmanager subcloud show
    """

    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    system_controller_ssh, result = pick_subcloud_with_fallback(
    availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
    lab_type=LabTypeEnum.SIMPLEX,
    load=required_release
    )

    subcloud_name = result.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, required_release))

    system_controller_patch = SoftwareListKeywords(system_controller_ssh).get_software_list().get_product_version_with_patch_by_state("deployed")
    matching_patches = [patch for patch in system_controller_patch if patch.startswith(f"{required_release}.")]
    validate_greater_than_or_equal(len(matching_patches), 1, f"Validate that a patch was found on the system controller for required release {required_release}. Available patches: {system_controller_patch}")
    target_release = max(matching_patches, key=lambda patch: int(patch.split(".")[-1]))

    system_controller_release_names = SoftwareListKeywords(system_controller_ssh).get_software_list().get_release_name_by_state("deployed")
    matching_release_names = [release_name for release_name in system_controller_release_names if release_name.endswith(target_release)]
    validate_greater_than_or_equal(len(matching_release_names), 1, f"Validate that a release name matching {target_release} was found on the system controller. Releases: {system_controller_release_names}")
    target_release_name = matching_release_names[0]

    subcloud_patch = SoftwareListKeywords(subcloud_ssh).get_software_list().system_has_patch()

    validate_not_none(system_controller_patch, "Validate that the system controller has a patch.")
    validate_none(subcloud_patch, "Validate that the subcloud has no patch.")

    prestage_subcloud(central_ssh=system_controller_ssh, subcloud_name=subcloud_name, release=required_release, subcloud_password=subcloud_password, for_sw_deploy=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_sw_deploy_versions = for_sw_deploy.split(",")
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(target_release, for_sw_deploy_versions, "Validate that the subcloud was prestaged to the target version.")

    subcloud_available_releases = SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_name_by_state("available")
    validate_list_contains(target_release_name, subcloud_available_releases, f"Validate that the subcloud software list shows {target_release_name} as available.")


@mark.p0
@mark.lab_has_subcloud
def test_verify_prestage_for_sw_deploy_option_n_minus_two_patching(request):
    """Test verify that when running prestage with option 
        --for-sw-deploy' enabled for an N-2 subcloud, shows N-2
        release as prestage_version in dcmanager subcloud show
    """

    required_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
    patch_state = "available"

    system_controller_ssh, result = pick_subcloud_with_fallback(
    availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
    lab_type=LabTypeEnum.SIMPLEX,
    load=required_release,
    multiple_releases=patch_state
    )

    subcloud_name = result.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, required_release))

    target_release_name = SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_name_by_state(patch_state)[0]
    target_release = re.search(r"(\d+\.\d+\.\d+)", target_release_name).group(1)

    prestage_subcloud(central_ssh=system_controller_ssh, subcloud_name=subcloud_name, release=required_release, subcloud_password=subcloud_password, for_sw_deploy=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_sw_deploy_versions = for_sw_deploy.split(",")
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(target_release, for_sw_deploy_versions, "Validate that the subcloud was prestaged to the target version.")

    subcloud_available_releases = SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_name_by_state("available")
    validate_list_contains(target_release_name, subcloud_available_releases, f"Validate that the subcloud software list shows {target_release_name} as available.")


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

    # Attempt prestage - expect immediate rejection due to alarm
    get_logger().log_info(f"Attempting prestage of {subcloud_name} (expecting rejection due to alarm)")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, for_sw_deploy=True, expect_rejection=True)

    # Retry prestage with --force - expect success despite alarm
    get_logger().log_info(f"Retrying prestage of {subcloud_name} with --force flag")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, for_sw_deploy=True, force=True)


# --- Consistency Tests ---


@mark.p0
@mark.lab_has_subcloud
def test_prestage_for_install_then_for_sw_deploy_preserves_for_install_version(request):
    """Verify that prestage --for-sw-deploy preserves the for-install value while updating for-sw-deploy.

    Test Steps:
        1. Prestage subcloud with --for-install (N-1 release)
        2. Validate prestage_versions for-install reflects the N-1 release
        3. Validate the N release is available on the subcloud
        4. Prestage the same subcloud with --for-sw-deploy (N release)
        5. Validate prestage_versions for-install is preserved (still N-1)
        6. Validate prestage_versions for-sw-deploy is updated to the N release

    Teardown:
        - Clear prestage_versions and prestage_status from the dcmanager database.
    """
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    target_prestage_release = str(CloudPlatformVersionManagerClass().get_sw_version())

    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load=required_release,
    )

    subcloud_name = result.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, required_release, target_prestage_release))

    software_list = SoftwareListKeywords(system_controller_ssh).get_software_list()
    available_release = software_list.get_release_name_by_state("available") + software_list.get_release_name_by_state("deployed")
    available_release_versions = [re.search(r"(\d+\.\d+)", release).group(1) for release in available_release]
    validate_list_contains(target_prestage_release, available_release_versions, "validate that the system controller has N release available")

    get_logger().log_test_case_step(f"Prestage subcloud {subcloud_name} with --for-install (release {required_release})")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=required_release, for_install=True)
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()
    for_install_before, for_sw_deploy_before = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_install_before_versions = for_install_before.split(",")
    validate_list_contains(required_release, for_install_before_versions, "Validate that for-install reflects the prestaged release.")

    get_logger().log_test_case_step(f"Prestage subcloud {subcloud_name} with --for-sw-deploy (release {target_prestage_release})")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=target_prestage_release, for_sw_deploy=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install_after, for_sw_deploy_after = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_sw_deploy_after_versions = for_sw_deploy_after.split(",")

    subcloud_software_list = SoftwareListKeywords(subcloud_ssh).get_software_list()
    subcloud_available_release = subcloud_software_list.get_release_name_by_state("available") + subcloud_software_list.get_release_name_by_state("deployed")
    subcloud_available_release_versions = [re.search(r"(\d+\.\d+)", release).group(1) for release in subcloud_available_release]
    validate_list_contains(target_prestage_release, subcloud_available_release_versions, "Validate that the subcloud has N release available.")
    for_sw_deploy_after_releases = [version.rsplit(".", 1)[0] for version in for_sw_deploy_after_versions]
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_equals(for_install_after, for_install_before, "Validate that for-install value was preserved after the for-sw-deploy prestage.")
    validate_list_contains(target_prestage_release, for_sw_deploy_after_releases, "Validate that for-sw-deploy value was updated to the new target release.")


@mark.p0
@mark.lab_has_subcloud
def test_prestage_for_sw_deploy_then_for_install_preserves_for_sw_deploy_version(request):
    """Verify that prestage --for-install preserves the for-sw-deploy value while updating for-install.

    Test Steps:
        1. Prestage subcloud with --for-sw-deploy (N release)
        2. Validate prestage_versions for-sw-deploy reflects the N release
        3. Prestage the same subcloud with --for-install (N-1 release)
        4. Validate prestage_versions for-sw-deploy is preserved (still N)
        5. Validate prestage_versions for-install is updated to the N-1 release

    Teardown:
        - Clear prestage_versions and prestage_status from the dcmanager database.
    """
    required_release = str(CloudPlatformVersionManagerClass().get_last_major_release())
    target_prestage_release = str(CloudPlatformVersionManagerClass().get_sw_version())

    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load=required_release,
    )

    subcloud_name = result.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, target_prestage_release, required_release))

    software_list = SoftwareListKeywords(system_controller_ssh).get_software_list()
    available_release = software_list.get_release_name_by_state("available") + software_list.get_release_name_by_state("deployed")
    available_release_versions = [re.search(r"(\d+\.\d+)", release).group(1) for release in available_release]
    validate_list_contains(target_prestage_release, available_release_versions, "validate that the system controller has N release available")

    get_logger().log_test_case_step(f"Prestage subcloud {subcloud_name} with --for-sw-deploy (release {target_prestage_release})")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=target_prestage_release, for_sw_deploy=True)
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()
    for_install_before, for_sw_deploy_before = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_sw_deploy_before_versions = for_sw_deploy_before.split(",")
    for_sw_deploy_before_releases = [version.rsplit(".", 1)[0] for version in for_sw_deploy_before_versions]
    validate_list_contains(target_prestage_release, for_sw_deploy_before_releases, "Validate that for-sw-deploy reflects the prestaged release.")

    subcloud_software_list = SoftwareListKeywords(subcloud_ssh).get_software_list()
    subcloud_available_release = subcloud_software_list.get_release_name_by_state("available") + subcloud_software_list.get_release_name_by_state("deployed")
    subcloud_available_release_versions = [re.search(r"(\d+\.\d+)", release).group(1) for release in subcloud_available_release]
    validate_list_contains(target_prestage_release, subcloud_available_release_versions, "Validate that the subcloud has N release available.")

    get_logger().log_test_case_step(f"Prestage subcloud {subcloud_name} with --for-install (release {required_release})")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=required_release, for_install=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install_after, for_sw_deploy_after = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_install_after_versions = for_install_after.split(",")
    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_list_contains(required_release, for_install_after_versions, "Validate that for-install value was updated to the new target release.")
    validate_equals(for_sw_deploy_after, for_sw_deploy_before, "Validate that for-sw-deploy value was preserved after the for-install prestage.")


@mark.p0
@mark.lab_has_subcloud
def test_prestage_for_sw_deploy_n_release_is_idempotent(request):
    """Verify that repeating prestage --for-sw-deploy with N release does not change prestage_versions.

    Test Steps:
        1. Prestage subcloud with --for-sw-deploy (N release)
        2. Validate prestage_versions for-sw-deploy reflects the N release
        3. Prestage the same subcloud again with --for-sw-deploy (N release)
        4. Validate prestage_versions for-sw-deploy is unchanged

    Teardown:
        - Clear prestage_versions and prestage_status from the dcmanager database.
    """
    target_prestage_release = str(CloudPlatformVersionManagerClass().get_sw_version())

    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
        load=target_prestage_release,
    )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    request.addfinalizer(lambda: teardown_clear_prestage_data(system_controller_ssh, subcloud_name, target_prestage_release))

    get_logger().log_test_case_step(f"Prestage subcloud {subcloud_name} with --for-sw-deploy (release {target_prestage_release})")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=target_prestage_release, for_sw_deploy=True)
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()
    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    for_sw_deploy_releases = [version.rsplit(".", 1)[0] for version in for_sw_deploy.split(",")]
    validate_list_contains(target_prestage_release, for_sw_deploy_releases, "Validate that for-sw-deploy reflects the prestaged release.")

    get_logger().log_test_case_step(f"Prestage subcloud {subcloud_name} again with --for-sw-deploy (release {target_prestage_release})")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=target_prestage_release, for_sw_deploy=True)
    prestage_status = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_status()
    prestage_versions_after = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    validate_equals(prestage_status, "complete", "Validate that the subcloud prestage operation has completed.")
    validate_equals(prestage_versions_after, prestage_versions, "Validate that prestage_versions is unchanged after repeating the prestage.")