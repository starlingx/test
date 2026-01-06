from pytest import mark

from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.files.file_keywords import FileKeywords

def teardown_local(subcloud_name: str):
    """Teardown function for local backup.

    Args:
        subcloud_name (str): subcloud name
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    get_logger().log_info("Removing test files")
    FileKeywords(central_ssh).delete_folder_with_sudo("subcloud_backup.yaml")
    FileKeywords(subcloud_ssh).delete_folder_with_sudo(f"{subcloud_name}_platform_backup_*.tgz")


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_without_docker_cache(request):
    """

    Test Steps:
        - Login and pull image from central cloud.
        - Verify that the image is not on local registry.
        - Run dcmanager CLI Backup with --local-only
        - Verify the docker images tarball does not contain
        the pulled image from the central cloud

    """
    central_docker_image = "registry.central:9001/registry.k8s.io/sig-storage/csi-snapshotter:v8.2.0"
    local_default_backup_path = "/opt/platform-backup/backups"
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_list = DcManagerSubcloudListKeywords(central_ssh)
    subcloud_name = subcloud_list.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id().get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()
    release = CloudPlatformVersionManagerClass().get_sw_version()
    registry_img_to_search = "csi-snapshotter"

    # Pulls an image from central cloud that is not on subcloud registry
    DockerImagesKeywords(subcloud_ssh).pull_image(central_docker_image)

    dc_manager_backup = DcManagerSubcloudBackupKeywords(central_ssh)

    # Path where backup file will be stored.
    local_path = f"/opt/platform-backup/backups/{release}/"

    def teardown():
        teardown_local(subcloud_name)

    request.addfinalizer(teardown)

    # Create a subcloud backup and verify the subcloud backup file in local custom path.
    get_logger().log_info(f"Create {subcloud_name} backup locally on custom path")
    dc_manager_backup.create_subcloud_backup(subcloud_password, subcloud_ssh, path=f"{local_path}{subcloud_name}_platform_backup_*.tgz", subcloud=subcloud_name, local_only=True, registry=True)

    files_in_bckp_dir = FileKeywords(subcloud_ssh).get_files_in_dir(f"{local_default_backup_path}/{release}/")
    img_tarball = [file for file in files_in_bckp_dir if "image_registry" in file][0]

    matches = FileKeywords(subcloud_ssh).find_in_tgz(
        f"{local_default_backup_path}/{release}/{img_tarball}", registry_img_to_search)
    validate_equals(matches, 0,f"Validate that no matches were found for {registry_img_to_search} in {img_tarball} tarball.")
