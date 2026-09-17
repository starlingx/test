"""Tests that /var/rootdirs/root/.docker/config.json is excluded from platform backups.

Validates the fix that excludes the Docker client credential file (config.json)
from platform backups. If a stale/expired credential is captured in a backup,
restore fails with 401 unauthorized when pulling images. These tests seed a
config.json with a (corrupted) credential, take a backup, and assert the
credential file is not present inside the backup tarball.

Scope: backup exclusion only. Restore is intentionally NOT exercised (that path
requires a private registry that is unavailable in this environment).
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.cloud_platform.ansible_playbook.ansible_playbook_keywords import AnsiblePlaybookKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.docker.config.docker_config_keywords import DockerConfigKeywords
from keywords.files.file_keywords import FileKeywords

# Path Docker uses to persist registry credentials on WRCP hosts.
DOCKER_CONFIG_PATH = "/var/rootdirs/root/.docker/config.json"
# Pattern that must NOT appear inside a backup tarball listing.
CONFIG_JSON_TAR_PATTERN = ".docker/config.json"
# Placeholder registry + credential used to seed a credential file for the test.
TEST_REGISTRY_URL = "ace-test-registry.local:5000"
TEST_AUTH_TOKEN = "YWNlLXRlc3Q6YWNlLXRlc3Q="


# --- Setup Helpers ---
def seed_and_corrupt_config(host_ssh: SSHConnection) -> None:
    """Ensure a corrupted credential config.json exists on the host before backup.

    Seeds a config.json with a placeholder registry auth entry, then corrupts the
    auth token to simulate stale credentials. This guarantees the file is present
    with credentials so the backup-exclusion assertion is meaningful.

    Args:
        host_ssh (SSHConnection): SSH connection to the host being backed up.
    """
    docker_config = DockerConfigKeywords(host_ssh)
    get_logger().log_info(f"Seeding {DOCKER_CONFIG_PATH} with a placeholder credential")
    seeded = docker_config.seed_config_with_auth(DOCKER_CONFIG_PATH, TEST_REGISTRY_URL, TEST_AUTH_TOKEN)
    validate_equals(seeded, True, "config.json seeded with credential before backup")

    corrupted_content = docker_config.corrupt_auth_field(DOCKER_CONFIG_PATH)
    validate_str_contains(corrupted_content, TEST_REGISTRY_URL, "Corrupted config.json still references the seeded registry")


# --- Teardown Helpers ---
def cleanup_docker_config(host_ssh: SSHConnection, backup_path: str) -> None:
    """Restore or remove the Docker config.json after the test.

    Decides based on what is on disk rather than on prior state: if a pre-test
    backup copy exists, restore it (and remove the copy); otherwise the config.json
    on disk was created by this test, so delete it. This guarantees the
    seeded/corrupted credentials are never left behind, even if the pre-test backup
    step failed to produce a copy.

    Args:
        host_ssh (SSHConnection): SSH connection to the host being backed up.
        backup_path (str): Path to the pre-test backup copy of config.json.
    """
    get_logger().log_teardown_step("Restore original Docker config.json")
    docker_config = DockerConfigKeywords(host_ssh)
    if docker_config.config_exists(backup_path):
        docker_config.restore_config(backup_path, DOCKER_CONFIG_PATH)
        docker_config.delete_config(backup_path)
    elif docker_config.config_exists(DOCKER_CONFIG_PATH):
        docker_config.delete_config(DOCKER_CONFIG_PATH)


def cleanup_backup_file(host_ssh: SSHConnection, backup_tarball_path: str) -> None:
    """Delete the specific platform backup tarball created by the test.

    Args:
        host_ssh (SSHConnection): SSH connection to the host holding the backup.
        backup_tarball_path (str): Absolute path to the tarball to delete.
    """
    get_logger().log_teardown_step("Delete the backup tarball created by the test")
    AnsiblePlaybookKeywords(host_ssh).delete_platform_backup_tarball(backup_tarball_path)


# --- Test Functions ---
@mark.p1
@mark.lab_is_simplex
def test_sx_backup_excludes_docker_config_json(request: FixtureRequest):
    """Verify AIO-SX platform backup excludes Docker config.json.

    Seeds a corrupted Docker credential file, takes a platform backup via the
    ansible backup playbook, and asserts config.json is not present inside the
    resulting backup tarball. Restore is not exercised.

    Preconditions:
        - AIO-SX system is healthy (no alarms, pods and apps healthy)

    Setup:
        - Establish SSH connection to the active controller
        - Back up any existing config.json
        - Seed and corrupt config.json to simulate stale credentials

    Test Steps:
        1. Take a platform backup via the ansible backup playbook
        2. Locate the backup tarball
        3. Verify config.json is not present inside the backup tarball

    Teardown:
        - Restore the original config.json (or remove the seeded one)
        - Delete the backup tarball created by the test
    """
    backup_dir = "/opt/backups"
    backup_config_path = "/tmp/ace-docker-config-backup.json"
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Validate system health before backup")
    HealthKeywords(ssh_connection).validate_healty_cluster()

    get_logger().log_setup_step("Back up existing Docker config.json")
    docker_config = DockerConfigKeywords(ssh_connection)
    request.addfinalizer(lambda: cleanup_docker_config(ssh_connection, backup_config_path))
    if docker_config.config_exists(DOCKER_CONFIG_PATH):
        docker_config.backup_config(DOCKER_CONFIG_PATH, backup_config_path)

    get_logger().log_setup_step("Seed and corrupt Docker config.json")
    seed_and_corrupt_config(ssh_connection)

    get_logger().log_test_case_step("Take a platform backup via the ansible backup playbook")
    backup_ok = AnsiblePlaybookKeywords(ssh_connection).ansible_playbook_backup(backup_dir)
    validate_equals(backup_ok, True, "Ansible platform backup completed successfully")

    get_logger().log_test_case_step("Locate the backup tarball")
    backup_tarball_path = AnsiblePlaybookKeywords(ssh_connection).get_latest_platform_backup_tarball(backup_dir)
    validate_not_equals(backup_tarball_path, "", "A platform backup tarball was created")
    request.addfinalizer(lambda: cleanup_backup_file(ssh_connection, backup_tarball_path))
    get_logger().log_info(f"Backup tarball under test: {backup_tarball_path}")

    get_logger().log_test_case_step("Verify config.json is not present inside the backup tarball")
    matches = FileKeywords(ssh_connection).find_in_tgz(backup_tarball_path, CONFIG_JSON_TAR_PATTERN)
    validate_equals(matches, 0, "Docker config.json is excluded from the platform backup tarball")


@mark.p1
@mark.lab_has_subcloud
def test_dc_subcloud_backup_excludes_docker_config_json(request: FixtureRequest):
    """Verify DC subcloud backup excludes Docker config.json.

    Seeds a corrupted Docker credential file on a healthy subcloud, takes a
    centralized subcloud backup via dcmanager, and asserts config.json is not
    present inside the resulting backup tarball on the system controller. Restore
    is not exercised.

    Preconditions:
        - At least one managed, healthy subcloud exists

    Setup:
        - Establish SSH connections to the system controller and subcloud
        - Back up any existing config.json on the subcloud
        - Seed and corrupt config.json on the subcloud to simulate stale credentials

    Test Steps:
        1. Create a centralized subcloud backup via dcmanager
        2. Wait for backup status to reach complete-central
        3. Locate the backup tarball on the system controller
        4. Verify config.json is not present inside the backup tarball

    Teardown:
        - Restore the original config.json on the subcloud (or remove the seeded one)
        - Delete the backup tarball created by the test
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Select a healthy managed subcloud")
    subcloud_name = DcManagerSubcloudListKeywords(central_ssh).get_healthy_subclouds_without_alarms()[0].get_name()
    get_logger().log_info(f"Using subcloud: {subcloud_name}")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    lab_subcloud = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_subcloud.get_admin_credentials().get_password()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    backup_config_path = "/tmp/ace-docker-config-backup.json"
    central_backup_dir = f"/opt/dc-vault/backups/{subcloud_name}/{subcloud_sw_version}"

    get_logger().log_setup_step("Back up existing Docker config.json on the subcloud")
    docker_config = DockerConfigKeywords(subcloud_ssh)
    request.addfinalizer(lambda: cleanup_docker_config(subcloud_ssh, backup_config_path))
    if docker_config.config_exists(DOCKER_CONFIG_PATH):
        docker_config.backup_config(DOCKER_CONFIG_PATH, backup_config_path)

    get_logger().log_setup_step("Seed and corrupt Docker config.json on the subcloud")
    seed_and_corrupt_config(subcloud_ssh)

    get_logger().log_test_case_step("Create a centralized subcloud backup via dcmanager")
    backup_keywords = DcManagerSubcloudBackupKeywords(central_ssh)
    backup_keywords.create_subcloud_backup(subcloud_password, central_ssh, path=central_backup_dir, subcloud=subcloud_name, release=subcloud_sw_version)

    get_logger().log_test_case_step("Wait for backup status to reach complete-central")
    backup_keywords.wait_for_backup_status_complete(subcloud_name, expected_status="complete-central")

    get_logger().log_test_case_step("Locate the backup tarball on the system controller")
    backup_tarball_path = AnsiblePlaybookKeywords(central_ssh).get_latest_platform_backup_tarball(central_backup_dir)
    validate_not_equals(backup_tarball_path, "", "A subcloud backup tarball was created on central")
    request.addfinalizer(lambda: cleanup_backup_file(central_ssh, backup_tarball_path))
    get_logger().log_info(f"Backup tarball under test: {backup_tarball_path}")

    get_logger().log_test_case_step("Verify config.json is not present inside the backup tarball")
    matches = FileKeywords(central_ssh).find_in_tgz(backup_tarball_path, CONFIG_JSON_TAR_PATTERN, is_sudo=True)
    validate_equals(matches, 0, "Docker config.json is excluded from the subcloud backup tarball")
