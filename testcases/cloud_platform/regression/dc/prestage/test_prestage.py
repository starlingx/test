import os
import re
from pytest import fail, mark

from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_greater_than_or_equal, validate_list_contains, validate_none, validate_not_equals, validate_not_none, validate_str_contains
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
from keywords.cloud_platform.version_info.cloud_platform_software_version import CloudPlatformSoftwareVersion
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords
from keywords.linux.log.log_grep_keywords import LogGrepKeywords
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
    /opt/software/metadata/available/starlingx-N.1-metadata.xml or
    /opt/software/metadata/available/WRCP-N.1-metadata.xml) for the
    releases used during the test's prestage calls.

    Args:
        central_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_name (str): Name of the subcloud to clear prestage data for.
        *releases (str): Release versions used during the test's prestage
            calls (e.g. the N release). Any metadata file whose name contains
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


def find_release_metadata_files(ssh_connection: SSHConnection, base_dir: str, release: str) -> list[str]:
    """Find release metadata files for a release under a base dir's 'deployed' or 'available' state subdirs.

    Checks '<base_dir>/deployed/' first, falling back to '<base_dir>/available/'
    if no match is found, since a prestaged release's metadata may land in
    either state directory depending on whether it's already deployed.

    Args:
        ssh_connection (SSHConnection): SSH connection to the host to search on.
        base_dir (str): Base metadata directory (e.g. "/opt/software/metadata"
            or "/opt/software/releases/metadata").
        release (str): Release version substring to match against file names.

    Returns:
        list[str]: Matching metadata file names from the first state
            subdirectory that has a match, or an empty list if none found.
    """
    file_keywords = FileKeywords(ssh_connection)
    for state in ("deployed", "available"):
        candidate_dir = f"{base_dir}/{state}/"
        metadata_files = file_keywords.get_files_in_dir(candidate_dir, is_sudo=True)
        state_matches = [metadata_file for metadata_file in metadata_files if release in metadata_file]
        if state_matches:
            return state_matches
    return []


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


# --- Edge Case Tests ---


@mark.p1
@mark.lab_has_subcloud
def test_prestage_blocked_when_subcloud_release_in_transient_state(request):
    """Verify prestage is blocked with a clear error when the subcloud release metadata is transient.

    Edge case: Subcloud has transient software state (deploying/removing).
    Expected result: Prestage blocked with clear error (existing behavior).

    Test Steps:
        1. Select the highest-value release in 'deployed' or 'available'
           state on the system controller (preferring 'deployed').
        2. Copy that release's on-disk metadata file from the system
           controller to the subcloud's home directory.
        3. Move the metadata file into the subcloud's 'deploying' state directory.
        4. Validate via 'software list' on the subcloud that the release is
           now reported as 'deploying'.
        5. Attempt prestage --for-sw-deploy and validate it fails.

    Teardown:
        - Remove the copied metadata file from the subcloud's 'deploying' directory.
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

    # Select the highest-value release in 'deployed' or 'available' state on
    # the system controller, preferring 'deployed'.
    system_controller_software_list = SoftwareListKeywords(system_controller_ssh).get_software_list()
    candidate_releases = system_controller_software_list.get_release_name_by_state("deployed") or system_controller_software_list.get_release_name_by_state("available")
    validate_greater_than_or_equal(len(candidate_releases), 1, "Validate that the system controller has at least one release in 'deployed' or 'available' state.")

    target_release_name = max(candidate_releases, key=lambda release_name: [int(part) for part in re.findall(r"\d+", release_name)])
    target_release_version = re.search(r"(\d+\.\d+)", target_release_name).group(1)
    target_release_state = system_controller_software_list.get_release_state_by_release_name(target_release_name)

    # On the system controller, release metadata always lives under the
    # legacy /opt/software/metadata/ path, regardless of release version.
    system_controller_metadata_base_dir = "/opt/software/metadata"

    # On the subcloud, metadata lives under /opt/software/releases/metadata/
    # for release N, and under the legacy /opt/software/metadata/ for older
    # ones (N-1, N-2).
    target_version_obj = CloudPlatformVersionManagerClass().get_product_version_object(target_release_version)
    subcloud_metadata_base_dir = "/opt/software/releases/metadata" if target_version_obj.is_after_or_equal_to(CloudPlatformSoftwareVersion.STARLINGX_12_0) else "/opt/software/metadata"

    system_controller_file_keywords = FileKeywords(system_controller_ssh)
    subcloud_file_keywords = FileKeywords(subcloud_ssh)

    source_metadata_path = f"{system_controller_metadata_base_dir}/{target_release_state}/{target_release_name}-metadata.xml"
    validate_equals(system_controller_file_keywords.file_exists(source_metadata_path), True, f"Validate that {source_metadata_path} exists on the system controller.")

    # No direct host-to-host scp keyword exists in the framework, so the
    # metadata file is copied via the test runner: download it from the
    # system controller, then upload it to the subcloud's home directory.
    local_metadata_path = os.path.join(ConfigurationManager.get_logger_config().get_test_case_resources_log_location(), f"{target_release_name}-metadata.xml")
    system_controller_file_keywords.download_file(source_metadata_path, local_metadata_path)

    subcloud_home_metadata_path = f"/home/sysadmin/{target_release_name}-metadata.xml"
    subcloud_file_keywords.upload_file(local_metadata_path, subcloud_home_metadata_path)

    deploying_metadata_path = f"{subcloud_metadata_base_dir}/deploying/{target_release_name}-metadata.xml"

    def teardown():
        if os.path.exists(local_metadata_path):
            os.remove(local_metadata_path)
        if subcloud_file_keywords.file_exists(deploying_metadata_path):
            subcloud_file_keywords.delete_file(deploying_metadata_path)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Move metadata for release {target_release_name} to 'deploying' state on the subcloud")
    subcloud_file_keywords.create_directory_with_sudo(f"{subcloud_metadata_base_dir}/deploying")
    subcloud_file_keywords.move_file(source=subcloud_home_metadata_path, destination=f"{subcloud_metadata_base_dir}/deploying/", sudo=True)

    subcloud_release_state = SoftwareListKeywords(subcloud_ssh).get_software_list().get_release_state_by_release_name(target_release_name)
    validate_equals(subcloud_release_state, "deploying", f"Validate that {target_release_name} is reported as 'deploying' on the subcloud.")

    get_logger().log_test_case_step(f"Attempt prestage --for-sw-deploy for release {target_release_version} - expect failure")
    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=target_release_version, for_sw_deploy=True, expect_fail=True)


@mark.p1
@mark.lab_has_subcloud
def test_prestage_fails_when_system_controller_metadata_dir_empty_for_version(request):
    """Verify the prestage playbook fails when the system controller metadata dir is empty for the requested version.

    Edge case: System controller metadata dir empty for requested version.
    Expected result: Command is rejected with an error stating the requested
    software version was not found/not deployed on the system controller.

    Test Steps:
        1. Select a subcloud running the N-1 release (fallback to N-2 if no
           N-1 subcloud is available), so the N-1/N-2 release itself is used
           as the prestage target (never a downgrade)
        2. Move every on-disk metadata file matching that release version
           (all patch levels) out of the system controller metadata dir to
           simulate an empty metadata dir for that version
        3. Request prestage --for-sw-deploy for that release and validate the
           command is rejected with a "requested software version not found
           or not deployed" style error
        4. Move the release metadata files back into place

    Teardown:
        - Restore the release metadata files to their original location on
          the system controller if the test did not already restore them.
    """
    target_release = str(CloudPlatformVersionManagerClass().get_last_major_release())

    try:
        system_controller_ssh, result = pick_subcloud_with_fallback(
            availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
            lab_type=LabTypeEnum.SIMPLEX,
            load=target_release,
        )
    except KeywordException:
        target_release = str(CloudPlatformVersionManagerClass().get_second_last_major_release())
        system_controller_ssh, result = pick_subcloud_with_fallback(
            availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
            lab_type=LabTypeEnum.SIMPLEX,
            load=target_release,
        )

    subcloud_name = result.get_name()
    ensure_subcloud_managed(system_controller_ssh, subcloud_name)

    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    metadata_base_dir = "/opt/software/metadata"
    system_controller_file_keywords = FileKeywords(system_controller_ssh)

    system_controller_software_list = SoftwareListKeywords(system_controller_ssh).get_software_list()
    stable_release_names = system_controller_software_list.get_release_name_by_state("deployed") + system_controller_software_list.get_release_name_by_state("available")

    def _find_metadata(release_name: str) -> str:
        """Return the on-disk metadata path for release_name in 'deployed' or 'available', or None."""
        for state in ("deployed", "available"):
            candidate_metadata = f"{metadata_base_dir}/{state}/{release_name}-metadata.xml"
            if system_controller_file_keywords.validate_file_exists_with_sudo(candidate_metadata):
                return candidate_metadata
        return None

    # Prestage --release is requested as MM.mm (no patch), and the request
    # is accepted as long as ANY on-disk metadata file matching that MM.mm
    # exists in a stable dir ('deployed' or 'available'), regardless of
    # patch level (MM.mm.p). So every on-disk metadata file whose name
    # contains the target MM.mm version must be moved out to truly empty
    # the metadata dir for that version.
    matching_metadata_files = [metadata_path for release_name in stable_release_names if target_release in release_name for metadata_path in [_find_metadata(release_name)] if metadata_path is not None]
    validate_greater_than_or_equal(len(matching_metadata_files), 1, f"Validate that at least one on-disk metadata file matches release version {target_release} on the system controller.")

    backup_locations = {metadata_path: f"/tmp/{metadata_path.rsplit('/', 1)[-1]}.bak" for metadata_path in matching_metadata_files}

    def teardown():
        for original_metadata, backup_metadata in backup_locations.items():
            if system_controller_file_keywords.validate_file_exists_with_sudo(backup_metadata):
                system_controller_file_keywords.move_file(source=backup_metadata, destination=original_metadata, sudo=True)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Move all metadata files matching release {target_release} out of the system controller metadata dir")
    for original_metadata, backup_metadata in backup_locations.items():
        system_controller_file_keywords.move_file(source=original_metadata, destination=backup_metadata, sudo=True)

    error_output = prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=target_release, for_sw_deploy=True, expect_rejection=True)
    validate_str_contains(error_output.lower(), "requested software version not found or not deployed in the system controller", f"Validate that the rejection error references the requested software version not being found for release {target_release} after removing its metadata from the system controller.")

    get_logger().log_test_case_step(f"Move all metadata files matching release {target_release} back into the system controller metadata dir")
    for original_metadata, backup_metadata in backup_locations.items():
        system_controller_file_keywords.move_file(source=backup_metadata, destination=original_metadata, sudo=True)


# --- Specific Validation Tests ---


@mark.p1
@mark.lab_has_subcloud
def test_prestage_system_controller_copies_metadata_from_releases_dir_for_n_release(request):
    """Verify the system controller copies release metadata from the new source path for releases >= N.

    Specific validation: System controller copies from correct source (releases >= N).
    Expected result: Ansible log shows the "Copy system controller release
    directory to subcloud" task ran, and the release metadata file is copied
    under /opt/software/releases/metadata/ (deployed/ or available/) on the subcloud.

    Test Steps:
        1. Prestage subcloud --for-sw-deploy with the current (N) release, which is >= N
        2. Grep the dcmanager ansible playbook log on the system controller for the
           "Copy system controller release directory to subcloud" task
        3. Validate the release metadata file was copied under
           /opt/software/releases/metadata/ on the subcloud

    Teardown:
        - Clear prestage_versions and prestage_status from the dcmanager database.
    """
    required_release_version = CloudPlatformVersionManagerClass().get_sw_version()
    required_release = str(required_release_version)
    validate_equals(required_release_version.is_after_or_equal_to(CloudPlatformSoftwareVersion.STARLINGX_12_0), True, f"Validate that the current release {required_release} is >= N for this test.")

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

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=required_release, for_sw_deploy=True)

    ansible_log_path = f"/var/log/dcmanager/ansible/{subcloud_name}_playbook_output.log"
    log_output = LogGrepKeywords(system_controller_ssh).grep_log_for_errors(ansible_log_path, "Copy system controller", tail=20)
    validate_not_equals(log_output, "", "Validate that a 'Copy system controller' task was found in the ansible playbook log.")
    validate_str_contains(
        log_output,
        "Copy system controller release directory to subcloud",
        "Validate that the 'Copy system controller release directory to subcloud' task ran, confirming the /opt/software/releases directory tree (which includes metadata) was synced for release >= N.",
    )

    # The prestaged release is already deployed on the system controller, so
    # its metadata is copied to the subcloud under the 'deployed' state
    # directory, not 'available' (which holds releases not yet deployed).
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    matching_files = find_release_metadata_files(subcloud_ssh, "/opt/software/releases/metadata", required_release)

    validate_greater_than_or_equal(len(matching_files), 1, f"Validate that release metadata for {required_release} was copied to /opt/software/releases/metadata/deployed/ or /opt/software/releases/metadata/available/ on the subcloud.")


@mark.p1
@mark.lab_has_subcloud
def test_prestage_system_controller_copies_metadata_from_legacy_dir_for_pre_n_minus_release(request):
    """Verify the system controller copies release metadata from the legacy source path for releases < N.

    Specific validation: System controller copies from correct source (releases < N).
    Expected result: Ansible log shows "Copy system controller /opt/software/metadata",
    and the release metadata file is copied under /opt/software/metadata/
    (deployed/ or available/) on the subcloud.

    Test Steps:
        1. Prestage subcloud --for-sw-deploy with the N-1 release, which is < N
        2. Grep the dcmanager ansible playbook log on the system controller for the
           "Copy system controller" task
        3. Validate the source path referenced is /opt/software/metadata
        4. Validate the release metadata file was copied under
           /opt/software/metadata/ on the subcloud

    Teardown:
        - Clear prestage_versions and prestage_status from the dcmanager database.
    """
    required_release_version = CloudPlatformVersionManagerClass().get_last_major_release()
    required_release = str(required_release_version)
    validate_equals(required_release_version.is_after_or_equal_to(CloudPlatformSoftwareVersion.STARLINGX_12_0), False, f"Validate that the release {required_release} is < N for this test.")

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

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=required_release, for_sw_deploy=True)

    ansible_log_path = f"/var/log/dcmanager/ansible/{subcloud_name}_playbook_output.log"
    log_output = LogGrepKeywords(system_controller_ssh).grep_log_for_errors(ansible_log_path, "Copy system controller", tail=20)
    validate_not_equals(log_output, "", "Validate that a 'Copy system controller' task was found in the ansible playbook log.")
    validate_str_contains(log_output, "/opt/software/metadata", "Validate that the system controller copied metadata from /opt/software/metadata for release < N.")

    # The prestaged release (N-1) is deployed on the system controller, so
    # its metadata is copied to the subcloud under the 'deployed' state
    # directory, not 'available' (which holds releases not yet deployed).
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    matching_files = find_release_metadata_files(subcloud_ssh, "/opt/software/metadata", required_release)

    validate_greater_than_or_equal(len(matching_files), 1, f"Validate that release metadata for {required_release} was copied to /opt/software/metadata/deployed/ or /opt/software/metadata/available/ on the subcloud.")


@mark.p1
@mark.lab_has_subcloud
def test_prestage_writes_metadata_to_correct_subcloud_path(request):
    """Verify prestage writes release metadata to the correct path on the subcloud.

    Specific validation: Script writes to correct subcloud path.
    Expected result: On a N-2 or N-1 subcloud, metadata appears under
    /opt/software/metadata/. On a N subcloud, metadata appears under
    /opt/software/releases/metadata/. The release used is already deployed
    on the system controller, so its metadata lands in the 'deployed' state
    subdirectory on the subcloud (checked, with 'available' as a fallback).

    Test Steps:
        1. Prestage subcloud --for-sw-deploy with the current (N) release
        2. Determine the expected metadata base directory based on the subcloud's release
        3. Validate the release metadata file exists under that directory
           (in 'deployed/' or 'available/')

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

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=required_release, for_sw_deploy=True)

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    current_version = CloudPlatformVersionManagerClass().get_sw_version()
    expected_metadata_base_dir = "/opt/software/releases/metadata" if current_version.is_after_or_equal_to(CloudPlatformSoftwareVersion.STARLINGX_12_0) else "/opt/software/metadata"

    # The prestaged release is the one currently deployed on the system
    # controller, so its metadata is copied to the subcloud under the
    # 'deployed' state directory, not 'available' (which holds releases
    # not yet deployed, e.g. newer patches). Check both to be safe.
    matching_files = find_release_metadata_files(subcloud_ssh, expected_metadata_base_dir, required_release)

    validate_greater_than_or_equal(len(matching_files), 1, f"Validate that release metadata for {required_release} was written to {expected_metadata_base_dir}/deployed/ or {expected_metadata_base_dir}/available/ on the subcloud.")


@mark.p1
@mark.lab_has_subcloud
def test_prestage_verify_prestage_version_for_sw_deploy(request):
    """Verify get-prestage-versions reports a non-None for-sw-deploy value after a successful prestage.

    Specific validation: Get-prestage-versions reports correctly.
    Expected result: Ansible log "Print prestage versions" task shows a non-None
    for-sw-deploy value after a successful --for-sw-deploy prestage.

    Test Steps:
        1. Prestage subcloud --for-sw-deploy with the current (N) release
        2. Validate dcmanager subcloud show reports a non-None for-sw-deploy value
        3. Grep the ansible playbook log for the "Print prestage versions" task
           and validate it does not report for-sw-deploy as None

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

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=required_release, for_sw_deploy=True)
    prestage_versions = DcManagerSubcloudShowKeywords(system_controller_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud_name).get_dcmanager_subcloud_show_object().get_prestage_versions()

    for_install, for_sw_deploy = re.search(r"for-install: (\S+) - for-sw-deploy: (\S+)", prestage_versions).groups()
    validate_not_equals(for_sw_deploy, "None", "Validate that dcmanager subcloud show reports a non-None for-sw-deploy value.")

    # The "Print prestage versions" task header and its actual output value
    # ('msg: "prestage_versions: for-install: ... - for-sw-deploy: ..."')
    # are on different lines in the ansible log, so grep directly for the
    # "for-sw-deploy:" text which only appears on the value line itself.
    ansible_log_path = f"/var/log/dcmanager/ansible/{subcloud_name}_playbook_output.log"
    log_output = LogGrepKeywords(system_controller_ssh).grep_log_for_errors(ansible_log_path, "prestage_versions.*for-sw-deploy", tail=5)
    validate_not_equals(log_output, "", "Validate that a 'prestage_versions' line referencing for-sw-deploy was found in the ansible playbook log.")
    validate_equals("for-sw-deploy: none" in log_output.lower(), False, "Validate that the ansible log does not report for-sw-deploy as None.")


@mark.p1
@mark.lab_has_subcloud
def test_prestage_sync_output_has_no_missing_file_errors(request):
    """Verify the prestage sync output does not contain 'cp: cannot stat' file-not-found errors.

    Specific validation: No 'cp: cannot stat' errors in sync output.
    Expected result: The "Show sync output" task in the ansible playbook log
    does not contain any file-not-found errors.

    Test Steps:
        1. Prestage subcloud --for-sw-deploy with the current (N) release
        2. Grep the ansible playbook log for "cp: cannot stat" errors
        3. Validate no such errors are present

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

    prestage_subcloud(system_controller_ssh, subcloud_name, subcloud_password, release=required_release, for_sw_deploy=True)

    ansible_log_path = f"/var/log/dcmanager/ansible/{subcloud_name}_playbook_output.log"
    log_output = LogGrepKeywords(system_controller_ssh).grep_log_for_errors(ansible_log_path, "cp: cannot stat")
    validate_equals(log_output, "", "Validate that the ansible playbook log does not contain 'cp: cannot stat' file-not-found errors.")


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