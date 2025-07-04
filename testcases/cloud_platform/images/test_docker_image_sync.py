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
