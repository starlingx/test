"""
Docker Image Sync Tests Using Manifest-Based Configuration

This module implements foundational tests that verify Docker images listed
in YAML manifest files can be pulled from remote registries (e.g., DockerHub),
tagged, and pushed into the local StarlingX registry (registry.local:9001).

Tests validate both positive and negative scenarios using a config-driven
approach that resolves registries dynamically via ConfigurationManager.

Key Behaviors:
- Validates sync logic from manifest to local registry via SSH.
- Verifies registry resolution order: source_registry, then manifest_registry_map,
  then default_source_registry.
- Supports flexible test-driven control over which manifests are synced.
- Logs missing images or partial sync failures for improved debugging.
"""

from pathlib import Path

import yaml
from pytest import FixtureRequest, fail, raises

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords


def run_manifest_sync_test(request: FixtureRequest, manifest_filename: str) -> None:
    """
    Executes a manifest-based sync test, pulling Docker images from source registries
    and pushing them to the local registry. Verifies that all expected images appear
    in the local registry.

    Args:
        request (FixtureRequest): pytest request object used to register cleanup finalizer.
        manifest_filename (str): Path to the manifest file in resources/.

    Raises:
        AssertionError: If any expected image is missing from the local registry.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    docker_config = ConfigurationManager.get_docker_config()
    local_registry = docker_config.get_registry("local_registry")
    manifest_paths = docker_config.get_image_manifest_files()

    manifest_path = next((p for p in manifest_paths if Path(p).name == manifest_filename), None)
    if not manifest_path:
        raise FileNotFoundError(f"Manifest {manifest_filename} not found in docker config.")

    DockerSyncImagesKeywords(ssh_connection).sync_images_from_manifest(manifest_path=manifest_path)

    with open(manifest_path, "r") as f:
        manifest = yaml.safe_load(f)

    docker_image_keywords = DockerImagesKeywords(ssh_connection)

    def cleanup():
        get_logger().log_info(f"Cleaning up images listed in {manifest_filename}...")
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        DockerSyncImagesKeywords(ssh_connection).remove_images_from_manifest(manifest_path=manifest_path)

    request.addfinalizer(cleanup)

    images = docker_image_keywords.list_images()
    actual_repos = [img.get_repository() for img in images]
    validation_errors = []

    for image in manifest["images"]:
        name = image["name"]
        tag = image["tag"]
        expected_ref = f"{local_registry.get_registry_url()}/{name}"

        get_logger().log_info(f"Checking local registry for: {expected_ref}:{tag}")
        if expected_ref not in actual_repos:
            msg = f"[{manifest_filename}] Expected image not found: {expected_ref}"
            get_logger().log_warning(msg)
            validation_errors.append(msg)

    if validation_errors:
        raise AssertionError("One or more expected images were not found:\n  - " + "\n  - ".join(validation_errors))


def test_sync_docker_images_valid_manifest_stx_dockerhub(request):
    """
    Validates that all images from a well-formed manifest can be pulled and synced into the local registry.
    """
    run_manifest_sync_test(request, "stx-test-images.yaml")


def test_sync_docker_images_invalid_manifest(request):
    """
    Negative test: verifies that syncing an invalid manifest raises KeywordException.

    This simulates real-world scenarios where image tags are missing or incorrectly referenced.

    Very simple brittle string matching is used to verify the exception message.
    """
    with raises(KeywordException, match="Image sync failed"):
        run_manifest_sync_test(request, "stx-test-images-invalid.yaml")


def test_sync_all_manifests_from_config(request):
    """
    Verifies that all manifest files listed in the Docker config can be successfully synced to local registry.

    This test ensures that ConfigurationManager.get_docker_config().get_image_manifest_files()
    is functional and can drive the sync logic dynamically.

    Note: Expected to currently fail if any manifest is invalid or any image fail sync fails.
    """
    manifest_paths = ConfigurationManager.get_docker_config().get_image_manifest_files()

    get_logger().log_info("Found image manifest paths in config: " + ", ".join(manifest_paths))

    for manifest_path in manifest_paths:
        manifest_name = Path(manifest_path).name
        run_manifest_sync_test(request, manifest_name)

    get_logger().log_info(f"All manifests synced successfully. Manifests: {', '.join(manifest_paths)}")


def test_sync_explicit_manifests(request):
    """
    Verifies that all manifest files listed in the test case can be successfully synced to local registry.

    Note: Expected to currently fail if any manifest is invalid or any image sync fails.
    """
    manifest_paths = [
        "stx-test-images.yaml",
        # "stx-test-images-invalid.yaml"
        # Uncomment the above line to include the invalid manifest in the test  (and expect failure).
    ]

    get_logger().log_info("Found image manifest paths in config: " + ", ".join(manifest_paths))

    for manifest_path in manifest_paths:
        manifest_name = Path(manifest_path).name
        run_manifest_sync_test(request, manifest_name)

    get_logger().log_info(f"All manifests synced successfully. Manifests: {', '.join(manifest_paths)}")


def test_invalid_manifest_logging(request):
    """
    Negative test: verifies that syncing an invalid manifest raises KeywordException.

    Logs only the image references that actually failed during sync.
    """
    manifest_path = "stx-test-images-invalid.yaml"

    try:
        run_manifest_sync_test(request, manifest_path)
    except KeywordException as e:
        # Parse individual failure lines from the exception message
        failure_lines = [line.strip(" -") for line in str(e).splitlines() if line.strip().startswith("-")]

        # Extract just the image reference (everything between 'image ' and ' from ')
        failed_images = []
        for line in failure_lines:
            if "image " in line and " from " in line:
                parts = line.split("image ", 1)[-1].split(" from ")[0].strip()
                failed_images.append(parts)
            else:
                failed_images.append(line)  # Fallback: use the whole line

        formatted_images = "\n\t- " + "\n\t- ".join(failed_images)
        get_logger().log_info(f"Negative image sync test passed.\n" f"\tManifest file: {manifest_path}\n" f"\tFailed images:{formatted_images}")

    else:
        fail("Expected KeywordException was not raised.")


# def test_sync_docker_images_valid_manifest_harbor(request):
#     """
#     Validates that all images from a well-formed manifest can be pulled and synced into the local registry from a harbor regsitry.
#     """
#     run_manifest_sync_test(request, "harbor-test-images.yaml")


# def test_sync_docker_images_mixed_registries(request):
#     """
#     Validates that images from a manifest with mixed registries (DockerHub and Harbor) can be pulled and synced into the local registry.
#     """
#     run_manifest_sync_test(request, "stx-test-images-mixed-registries.yaml")


def test_sync_single_busybox_image(request: FixtureRequest):
    """
    Sync a single image (busybox:1.36.1) from the manifest to the local registry,
    validate it exists, and clean up afterwards.

    This test validates the sync_image_from_manifest() method which allows
    selective syncing of individual images rather than entire manifests.
    """
    manifest_path = get_stx_resource_path("resources/image_manifests/stx-third-party-test-images.yaml")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Removing busybox image from local registry")
        docker_sync_keywords.remove_image_from_manifest(image_name="busybox", image_tag="1.36.1", manifest_path=manifest_path)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step("Syncing busybox image from manifest")
    docker_sync_keywords.sync_image_from_manifest(image_name="busybox", image_tag="1.36.1", manifest_path=manifest_path)

    get_logger().log_test_case_step("Validating busybox image exists in local registry")
    assert docker_sync_keywords.image_exists_in_local_registry(image_name="busybox", image_tag="1.36.1")


def test_sync_third_party_images_to_local_registry(request: FixtureRequest):
    """
    Sync required 3rd party Docker images from source registries to local registry.

    This test ensures all common sanity test images are preloaded into registry.local.
    Uses the stx-third-party-test-images.yaml manifest which contains public images
    from DockerHub, k8s.gcr.io, and other public registries.
    """
    manifest_path = get_stx_resource_path("resources/image_manifests/stx-third-party-test-images.yaml")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    docker_keywords = DockerSyncImagesKeywords(ssh_connection)

    def cleanup():
        get_logger().log_teardown_step("Removing third-party images from manifest")
        docker_keywords.remove_images_from_manifest(manifest_path)

    request.addfinalizer(cleanup)

    get_logger().log_test_case_step(f"Syncing Docker images from manifest: {manifest_path}")
    docker_keywords.sync_images_from_manifest(manifest_path)

    get_logger().log_test_case_step("Validating all images exist in local registry")
    docker_keywords.manifest_images_exist_in_local_registry(manifest_path)

    get_logger().log_info("Successfully synced all 3rd party test images")


def test_remove_third_party_images_from_local_registry():
    """
    Remove third-party Docker images from registry.local that were synced from manifest.

    This test ensures cleanup of common sanity/networking images after test execution.
    Can be run independently or as part of test cleanup verification.
    """
    manifest_path = get_stx_resource_path("resources/image_manifests/stx-third-party-test-images.yaml")

    get_logger().log_test_case_step("Connecting to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step(f"Removing Docker images listed in: {manifest_path}")
    docker_keywords = DockerSyncImagesKeywords(ssh_connection=ssh_connection)
    docker_keywords.remove_images_from_manifest(manifest_path)

    get_logger().log_info("Successfully removed all third-party test images")


def test_single_image_sync_and_removal_workflow(request: FixtureRequest):
    """
    Test the complete workflow of syncing and removing a single image.

    This test validates:
    1. Single image sync from manifest
    2. Image validation in local registry
    3. Single image removal from manifest
    4. Cleanup verification
    """
    manifest_path = get_stx_resource_path("resources/image_manifests/stx-third-party-test-images.yaml")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    docker_sync_keywords = DockerSyncImagesKeywords(ssh_connection)

    # Test image: calico/ctl:v3.27.0 (from the third-party manifest)
    test_image_name = "calico/ctl"
    test_image_tag = "v3.27.0"

    def cleanup():
        get_logger().log_teardown_step(f"Final cleanup: removing {test_image_name}:{test_image_tag}")
        try:
            docker_sync_keywords.remove_image_from_manifest(image_name=test_image_name, image_tag=test_image_tag, manifest_path=manifest_path)
        except Exception as e:
            get_logger().log_warning(f"Cleanup failed (expected if test passed): {e}")

    request.addfinalizer(cleanup)

    # Step 1: Sync the single image
    get_logger().log_test_case_step(f"Syncing {test_image_name}:{test_image_tag} from manifest")
    docker_sync_keywords.sync_image_from_manifest(image_name=test_image_name, image_tag=test_image_tag, manifest_path=manifest_path)

    # Step 2: Validate it exists in local registry
    get_logger().log_test_case_step(f"Validating {test_image_name}:{test_image_tag} exists in local registry")
    assert docker_sync_keywords.image_exists_in_local_registry(image_name=test_image_name, image_tag=test_image_tag), f"Image {test_image_name}:{test_image_tag} should exist in local registry after sync"

    # Step 3: Remove the single image
    get_logger().log_test_case_step(f"Removing {test_image_name}:{test_image_tag} from local registry")
    docker_sync_keywords.remove_image_from_manifest(image_name=test_image_name, image_tag=test_image_tag, manifest_path=manifest_path)

    # Step 4: Validate it no longer exists (optional verification)
    get_logger().log_test_case_step(f"Verifying {test_image_name}:{test_image_tag} was removed")
    assert not docker_sync_keywords.image_exists_in_local_registry(image_name=test_image_name, image_tag=test_image_tag), f"Image {test_image_name}:{test_image_tag} should not exist in local registry after removal"

    get_logger().log_info(f"Successfully completed single image sync/removal workflow for {test_image_name}:{test_image_tag}")
