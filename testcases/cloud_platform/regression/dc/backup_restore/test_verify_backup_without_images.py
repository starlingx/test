from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.registry.system_registry_image_list_keywords import SystemRegistryImageListKeywords
from keywords.cloud_platform.system.registry.system_registry_image_tags_keywords import SystemRegistryImageTagsKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from keywords.docker.login.docker_login_keywords import DockerLoginKeywords
from keywords.files.file_keywords import FileKeywords

CENTRAL_REGISTRY_URL = "registry.central:9001"


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


def teardown_pulled_image(subcloud_name: str, image: str):
    """Teardown function that removes the image pulled into the subcloud docker image cache.

    Args:
        subcloud_name (str): subcloud name
        image (str): full reference of the image that was pulled
    """
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    get_logger().log_info(f"Removing pulled image {image} from the {subcloud_name} docker image cache")
    DockerImagesKeywords(subcloud_ssh).remove_image(image)


def get_registry_image_names(ssh_connection: SSHConnection) -> list[str]:
    """Get the names of the images in the docker-distribution registry of a controller.

    Args:
        ssh_connection (SSHConnection): SSH connection to the controller (system controller or subcloud).

    Returns:
        list[str]: image names as reported by 'system registry-image-list'.
    """
    return SystemRegistryImageListKeywords(ssh_connection).get_registry_image_list().get_image_names()


def pick_central_only_image(central_ssh: SSHConnection, subcloud_registry_images: list[str]) -> tuple[str, str]:
    """Pick an image that is in the system controller registry but not in the subcloud registry.

    Args:
        central_ssh (SSHConnection): SSH connection to the system controller.
        subcloud_registry_images (list[str]): names of the images in the subcloud registry.

    Returns:
        tuple[str, str]: image name and one of its tags.

    Raises:
        KeywordException: If no tagged image exists only in the system controller registry.
    """
    central_registry_images = get_registry_image_names(central_ssh)
    candidates = sorted(set(central_registry_images) - set(subcloud_registry_images))
    tags_keywords = SystemRegistryImageTagsKeywords(central_ssh)
    for candidate in candidates:
        tags = tags_keywords.get_image_tags(candidate).get_tag_names()
        if tags:
            return candidate, tags[0]

    raise KeywordException("No tagged image exists only in the system controller registry, so the premise of the test cannot be established. " f"Candidates without tags: {candidates}. System controller registry: {sorted(central_registry_images)}. Subcloud registry: {sorted(subcloud_registry_images)}")


@mark.p0
@mark.subcloud_lab_is_simplex
def test_verify_backup_without_docker_cache(request):
    """

    Test Steps:
        - Pick an image that is on the central cloud registry but not on the subcloud registry.
        - Verify that the image is not on the subcloud local registry.
        - Login to the central cloud registry and pull the image into the subcloud docker image cache.
        - Run dcmanager CLI Backup with --local-only --registry-images
        - Verify the docker images tarball does not contain
        the pulled image from the central cloud

    """
    local_default_backup_path = "/opt/platform-backup/backups"
    central_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        lab_type=LabTypeEnum.SIMPLEX,
    )
    subcloud_name = result.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()
    release = CloudPlatformVersionManagerClass().get_sw_version()

    # Select an image that the subcloud registry does not hold.
    get_logger().log_info("Selecting an image that is on the central registry but not on the subcloud registry")
    subcloud_registry_images = get_registry_image_names(subcloud_ssh)
    image_name, image_tag = pick_central_only_image(central_ssh, subcloud_registry_images)
    central_docker_image = f"{CENTRAL_REGISTRY_URL}/{image_name}:{image_tag}"
    registry_img_to_search = f"repositories/{image_name}"

    # The test is only meaningful if the image is absent from the subcloud registry.
    validate_equals(image_name in subcloud_registry_images, False, f"Validate that {image_name} is not on the {subcloud_name} local registry")

    # Registered before the pull so the docker image cache is cleaned even if the pull or a later step fails.
    request.addfinalizer(lambda: teardown_pulled_image(subcloud_name, central_docker_image))

    # Pulls an image from central cloud that is not on subcloud registry
    get_logger().log_info(f"Login to {CENTRAL_REGISTRY_URL} and pull {central_docker_image} on {subcloud_name}")
    central_registry = ConfigurationManager.get_docker_config().get_local_registry()
    DockerLoginKeywords(subcloud_ssh).login(central_registry.get_user_name(), central_registry.get_password(), CENTRAL_REGISTRY_URL)
    docker_images_keywords = DockerImagesKeywords(subcloud_ssh)
    docker_images_keywords.pull_image(central_docker_image)

    cached_repositories = [image.get_repository() for image in docker_images_keywords.list_images()]
    validate_equals(f"{CENTRAL_REGISTRY_URL}/{image_name}" in cached_repositories, True, f"Validate that {central_docker_image} is in the {subcloud_name} docker image cache")

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

    matches = FileKeywords(subcloud_ssh).find_in_tgz(f"{local_default_backup_path}/{release}/{img_tarball}", registry_img_to_search)
    validate_equals(matches, 0, f"Validate that no matches were found for {registry_img_to_search} in {img_tarball} tarball.")
