from pathlib import Path

import yaml

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords


class DockerSyncImagesKeywords(BaseKeyword):
    """
    Provides functionality for Docker image synchronization across registries.

    Supports pulling from source, tagging, and pushing to the local registry
    based on manifest-driven configuration.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize DockerSyncImagesKeywords with an SSH connection.

        Args:
            ssh_connection (SSHConnection): Active SSH connection to the system under test.
        """
        self.ssh_connection = ssh_connection
        self.docker_images_keywords = DockerImagesKeywords(ssh_connection)
        self.docker_load_keywords = DockerLoadImageKeywords(ssh_connection)

    def sync_images_from_manifest(self, manifest_path: str) -> None:
        """
        Syncs Docker images listed in a YAML manifest from a source registry into the local registry.

        For each image:
        - Pull from the resolved source registry.
        - Tag for the local registry (e.g., registry.local:9001).
        - Push to the local registry.

        Registry credentials and mappings are resolved using ConfigurationManager.get_docker_config(),
        which loads config from `config/docker/files/default.json5` or a CLI override.

        Registry resolution priority (from most to least specific):
        1. "source_registry" field on the individual image entry (in the manifest)
        2. "manifest_registry_map" entry matching the full manifest path (in config)
        3. "default_source_registry" defined globally in config

        Expected manifest format:
        ```yaml
        images:
          - name: "starlingx/test-image"
            tag: "tag-x"
            # Optional: source_registry: "dockerhub"
        ```

        Notes:
        - Registry URLs and credentials must be defined in config, not in the manifest.
          Any such values in the manifest are ignored.
        - Each image entry must include "name" and "tag".

        Args:
            manifest_path (str): Full path to the YAML manifest file.

        Raises:
            KeywordException: If one or more image sync operations fail.
            ValueError: If no registry can be resolved for an image.
        """
        docker_config = ConfigurationManager.get_docker_config()
        local_registry = docker_config.get_registry("local_registry")
        default_registry_name = docker_config.get_default_source_registry_name()

        with open(manifest_path, "r") as f:
            manifest = yaml.safe_load(f)

        manifest_registry_name = docker_config.get_registry_for_manifest(manifest_path)

        if "images" not in manifest:
            raise ValueError(f"Manifest at {manifest_path} is missing required 'images' key")

        failures = []

        for image in manifest["images"]:
            name = image["name"]
            tag = image["tag"]

            # Resolve source registry in order of precedence:
            # 1) per-image override ("source_registry" in manifest)
            # 2) per-manifest default (manifest_registry_map in config)
            # 3) global fallback (default_source_registry in config)
            source_registry_name = image.get("source_registry") or manifest_registry_name or default_registry_name

            if not source_registry_name:
                raise ValueError(f"Image '{name}:{tag}' has no 'source_registry' and no default_source_registry is set in config.")
            try:
                source_registry = docker_config.get_registry(source_registry_name)

                source_image = f"{source_registry.get_registry_url()}/{name}:{tag}"
                target_image = f"{local_registry.get_registry_url()}/{name}:{tag}"

                get_logger().log_info(f"Pulling {source_image}")
                self.docker_images_keywords.pull_image(source_image)

                get_logger().log_info(f"Tagging {source_image} -> {target_image}")
                self.docker_load_keywords.tag_docker_image_for_registry(
                    image_name=source_image,
                    tag_name=f"{name}:{tag}",
                    registry=local_registry,
                )

                get_logger().log_info(f"Pushing {target_image}")
                self.docker_load_keywords.push_docker_image_to_registry(
                    tag_name=f"{name}:{tag}",
                    registry=local_registry,
                )

            except Exception as e:
                error_msg = f"Failed to sync image {name}:{tag} from {source_registry_name}: {e}"
                get_logger().log_error(error_msg)
                failures.append(error_msg)

        if failures:
            raise KeywordException(f"Image sync failed for manifest '{manifest_path}':\n  - " + "\n  - ".join(failures))

    def remove_images_from_manifest(self, manifest_path: str) -> None:
        """
        Removes Docker images listed in the manifest from the local system.

        Each image entry is removed using up to three tag formats to ensure all tag variants are cleared:
        1. source_registry/image:tag   (skipped if source is docker.io; see note below)
        2. local_registry/image:tag    (e.g., image pushed to registry.local)
        3. image:tag                   (default short form used by Docker)

        This ensures removal regardless of how the image was tagged during sync, supports
        idempotency, and handles Docker's implicit normalization of tags.

        Notes:
            - docker.io-prefixed references are skipped because Docker stores these as image:tag.
            - Removal is attempted even for images that were never successfully synced.

        Args:
            manifest_path (str): Path to the manifest YAML file containing image entries.

        Raises:
            KeywordException: If the manifest cannot be read, parsed, or is missing required fields.
        """
        docker_config = ConfigurationManager.get_docker_config()
        local_registry = docker_config.get_registry("local_registry")

        try:
            with open(manifest_path, "r") as f:
                manifest = yaml.safe_load(f)
        except Exception as e:
            raise KeywordException(f"Failed to load manifest '{manifest_path}': {e}")

        if "images" not in manifest:
            raise KeywordException(f"Manifest '{manifest_path}' missing required 'images' key")

        for image in manifest["images"]:
            name = image["name"]
            tag = image["tag"]

            source_registry_name = docker_config.get_effective_source_registry_name(image, manifest_path)
            if not source_registry_name:
                get_logger().log_debug(f"Skipping cleanup for image {name}:{tag} (no source registry resolved)")
                continue

            source_registry = docker_config.get_registry(source_registry_name)
            source_url = source_registry.get_registry_url()

            # Always try to remove these two references
            refs = [
                f"{local_registry.get_registry_url()}/{name}:{tag}",
                f"{name}:{tag}",
            ]

            # Optionally add full source registry tag if not DockerHub
            if "docker.io" not in source_url:
                refs.insert(0, f"{source_url}/{name}:{tag}")
            else:
                get_logger().log_debug(f"Skipping full docker.io-prefixed tag for {source_url}/{name}:{tag}")

            for ref in refs:
                self.docker_images_keywords.remove_image(ref)

    def validate_manifest_images_exist(self, manifest_path: str, fail_on_missing: bool = True) -> bool:
        """
        Validates that all images listed in a manifest are present in the local Docker registry.

        This is typically used after syncing images via `sync_images_from_manifest` to ensure that
        each expected image was successfully pushed to the local registry (e.g., registry.local:9001).

        If `fail_on_missing` is True, the method raises a `KeywordException` if any expected image
        is missing. If False, it logs the error but does not raise, allowing non-blocking verification.

        Args:
            manifest_path (str): Path to the manifest YAML file containing image entries.
            fail_on_missing (bool): Whether to raise an exception on missing images. Defaults to True.

        Returns:
            bool: True if all expected images were found, False if any were missing and `fail_on_missing` is False.

        Raises:
            KeywordException: If the manifest is invalid or, when `fail_on_missing` is True, one or more expected images are missing.
        """
        docker_config = ConfigurationManager.get_docker_config()
        local_registry = docker_config.get_registry("local_registry")

        try:
            with open(manifest_path, "r") as f:
                manifest = yaml.safe_load(f)
        except Exception as e:
            raise KeywordException(f"Failed to load manifest '{manifest_path}': {e}")

        if "images" not in manifest:
            raise KeywordException(f"Manifest '{manifest_path}' missing required 'images' key")

        images = self.docker_images_keywords.list_images()
        actual_repos = [img.get_repository() for img in images]
        validation_errors = []

        for image in manifest["images"]:
            name = image["name"]
            tag = image["tag"]
            expected_ref = f"{local_registry.get_registry_url()}/{name}"

            get_logger().log_info(f"Checking local registry for: {expected_ref}:{tag}")
            if expected_ref not in actual_repos:
                msg = f"[{Path(manifest_path).name}] Expected image not found: {expected_ref}"
                get_logger().log_warning(msg)
                validation_errors.append(msg)

        if validation_errors:
            message = "One or more expected images were not found in the local registry:\n  - " + "\n  - ".join(validation_errors)
            if fail_on_missing:
                raise KeywordException(message)
            else:
                get_logger().log_error(message)
                return False

        return True
