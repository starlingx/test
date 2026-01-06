from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_greater_than
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords
from keywords.files.file_keywords import FileKeywords


def teardown_local(subcloud_name: str, local_path: str):
    """Teardown function for local backup.

    Args:
        subcloud_name (str): subcloud name
        local_path (str): local backup path
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    get_logger().log_info("Removing test files")
    FileKeywords(central_ssh).delete_file("subcloud_backup.yaml")
    FileKeywords(subcloud_ssh).delete_file(f"{local_path}/{subcloud_name}_platform_backup_*.tgz")


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_with_custom_docker_image(request):
    """

    Test Steps:
        - Login and pull image from docker repo.
        - Verify that the image is not on local registry.
        - Run dcmanager CLI Backup with --local-only
        - Verify the docker images tarball does not contain
        the pulled image from the central cloud

    """
    docker_config = ConfigurationManager.get_docker_config()
    docker_img = "hello-world:latest"
    local_registry = docker_config.get_local_registry()
    local_default_backup_path = "/opt/platform-backup/backups"
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_list = DcManagerSubcloudListKeywords(central_ssh)
    subcloud_name = subcloud_list.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id().get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Pulls an image from central cloud that is not on subcloud registry
    DockerImagesKeywords(subcloud_ssh).pull_image(docker_img)
    DockerLoadImageKeywords(subcloud_ssh).tag_docker_image_for_registry(docker_img, docker_img, local_registry)
    DockerLoadImageKeywords(subcloud_ssh).push_docker_image_to_registry(docker_img, local_registry)

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path where backup file will be stored.
    local_path = f"/opt/platform-backup/backups/{release}/"

    def teardown():
        teardown_local(subcloud_name, local_path=local_path)

    request.addfinalizer(teardown)

    # Create a subcloud backup and verify the subcloud backup file in local custom path.
    get_logger().log_info(f"Create {subcloud_name} backup locally on custom path")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{local_path}{subcloud_name}_platform_backup_*.tgz", subcloud=subcloud_name, local_only=True, registry=True)

    get_logger().log_info("Checking if first backup was created on Central")
    DcManagerSubcloudBackupKeywords(central_ssh).wait_for_backup_status_complete(subcloud_name, expected_status="complete-local")

    files_in_bckp_dir = FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_default_backup_path}/{release}/")
    img_tarball = [file for file in files_in_bckp_dir if "image_registry" in file][0]

    matches = FileKeywords(subcloud_ssh).find_in_tgz(f"{local_default_backup_path}/{release}/{img_tarball}", "repositories/hello-world")
    validate_greater_than(matches, 0, f"Validate that were found mathces for hello-world in {img_tarball} tarball.")
