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

    def _load_and_validate_manifest(self, manifest_path: str) -> dict:
        """
        Load and validate manifest structure.

        Args:
            manifest_path (str): Path to the manifest YAML file.

        Returns:
            dict: Loaded manifest data.

        Raises:
            KeywordException: If the manifest cannot be loaded or is missing required fields.
        """
        try:
            with open(manifest_path, "r") as f:
                manifest = yaml.safe_load(f)
        except Exception as e:
            raise KeywordException(f"Failed to load manifest '{manifest_path}': {e}")

        if "images" not in manifest:
            raise KeywordException(f"Manifest '{manifest_path}' missing required 'images' key")

        return manifest

    def _find_image_in_manifest(self, manifest: dict, image_name: str, image_tag: str, manifest_path: str) -> dict:
        """
        Find and validate a specific image entry in manifest.

        Args:
            manifest (dict): Loaded manifest data.
            image_name (str): Name of the image to find.
            image_tag (str): Tag of the image to find.
            manifest_path (str): Path to manifest file (for error messages).

        Returns:
            dict: The matching image entry.

        Raises:
            KeywordException: If image is not found or duplicate entries exist.
        """
        matches = [img for img in manifest["images"] if img["name"] == image_name and img["tag"] == image_tag]

        if not matches:
            raise KeywordException(f"Image '{image_name}:{image_tag}' not found in manifest '{manifest_path}'")

        if len(matches) > 1:
            base_message = f"Duplicate entries found for '{image_name}:{image_tag}' in manifest '{manifest_path}'. Each image:tag combination must be unique."
            duplicate_entries_details = "\n".join([str(entry) for entry in matches])
            get_logger().log_error(f"{base_message}\n{duplicate_entries_details}")
            raise KeywordException(base_message)

        return matches[0]

    def _sync_single_image_from_manifest(self, image: dict, manifest_path: str) -> None:
        """
        Sync a single image using the pull/tag/push pattern.

        Args:
            image (dict): Image entry from manifest with 'name' and 'tag' keys.
            manifest_path (str): Path to manifest file (for registry resolution).

        Raises:
            KeywordException: If no registry can be resolved or sync operations fail.
        """
        docker_config = ConfigurationManager.get_docker_config()
        local_registry = docker_config.get_registry("local_registry")

        name = image["name"]
        tag = image["tag"]

        # Resolve the source registry using the config resolution precedence
        source_registry_name = docker_config.get_effective_source_registry_name(image, manifest_path)

        if not source_registry_name:
            raise KeywordException(f"Image '{name}:{tag}' has no registry resolved (manifest: {manifest_path}).")

        source_registry = docker_config.get_registry(source_registry_name)

        registry_url = source_registry.get_registry_url()
        path_prefix = source_registry.get_path_prefix()
        if path_prefix:
            # Normalize path_prefix to ensure proper slash formatting
            normalized_prefix = path_prefix.strip("/") + "/"
            source_image = f"{registry_url}/{normalized_prefix}{name}:{tag}"
        else:
            source_image = f"{registry_url}/{name}:{tag}"
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

    def _build_image_references_for_removal(self, image_name: str, image_tag: str, manifest_path: str) -> list:
        """
        Build list of image references to attempt removal for.

        Args:
            image_name (str): Name of the image.
            image_tag (str): Tag of the image.
            manifest_path (str): Path to manifest file (for registry resolution).

        Returns:
            list: List of image references to try removing.
        """
        docker_config = ConfigurationManager.get_docker_config()
        local_registry = docker_config.get_registry("local_registry")

        source_registry_name = docker_config.get_effective_source_registry_name({"name": image_name, "tag": image_tag}, manifest_path)

        if not source_registry_name:
            get_logger().log_debug(f"Skipping cleanup for image {image_name}:{image_tag} (no source registry resolved)")
            return []

        source_registry = docker_config.get_registry(source_registry_name)
        source_url = source_registry.get_registry_url()
        path_prefix = source_registry.get_path_prefix()

        # Always try to remove these two references
        refs = [
            f"{local_registry.get_registry_url()}/{image_name}:{image_tag}",
            f"{image_name}:{image_tag}",
        ]

        # Optionally add full source registry tag if not DockerHub
        if "docker.io" not in source_url:
            if path_prefix:
                # Normalize path_prefix to ensure proper slash formatting
                normalized_prefix = path_prefix.strip("/") + "/"
                refs.insert(0, f"{source_url}/{normalized_prefix}{image_name}:{image_tag}")
            else:
                refs.insert(0, f"{source_url}/{image_name}:{image_tag}")
        else:
            get_logger().log_debug(f"Skipping full docker.io-prefixed tag for {source_url}/{path_prefix}{image_name}:{image_tag}")

        return refs

    def sync_images_from_manifest(self, manifest_path: str) -> None:
        """
        Syncs Docker images listed in a YAML manifest from a source registry into the local registry.

        For each image:
        - Pull from the resolved source registry.
        - Tag for the local registry (e.g., registry.local:9001).
        - Push to the local registry.

        Registry credentials and mappings are resolved using ConfigurationManager.get_docker_config(),
        which loads config from `config/docker/files/default.json5` or a CLI override.

        Registry resolution behavior:

        1) If a manifest entry exists in "manifest_registry_map":
        - If "override" is true, all images in the manifest use the manifest "manifest_registry" (must be set).
        - If "override" is false:
            a. If an image defines "source_registry", it is used.
            b. If no per-image "source_registry" is specified, but the manifest "manifest_registry" is set, it is used.
            c. Otherwise, "default_source_registry" is used.
        2) If no manifest entry exists:
        - If an image defines "source_registry", it is used.
        - Otherwise, "default_source_registry" is used.

        Expected manifest format:
        ```yaml
        images:
          - name: "starlingx/test-image"
            tag: "tag-x"
            source_registry: "dockerhub"  # Optional
        ```

        Notes:
        - Registry URLs and credentials must be defined in config, not in the manifest.
        Any such values in the manifest are ignored.
        - Each image entry must include "name" and "tag".

        Args:
            manifest_path (str): Full path to the YAML manifest file.

        Raises:
            KeywordException: If one or more image sync operations fail, or if no registry can be resolved for an image.
        """
        manifest = self._load_and_validate_manifest(manifest_path)
        failures = []

        for image in manifest["images"]:
            try:
                self._sync_single_image_from_manifest(image, manifest_path)
            except Exception as e:
                error_msg = f"Failed to sync image {image['name']}:{image['tag']}: {e}"
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
        manifest = self._load_and_validate_manifest(manifest_path)

        for image in manifest["images"]:
            name = image["name"]
            tag = image["tag"]

            refs = self._build_image_references_for_removal(name, tag, manifest_path)

            for ref in refs:
                self.docker_images_keywords.remove_image(ref)

    def manifest_images_exist_in_local_registry(self, manifest_path: str, fail_on_missing: bool = True) -> bool:
        """
        Checks that all images listed in a manifest are present in the local Docker registry.

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

        manifest = self._load_and_validate_manifest(manifest_path)

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

    def sync_image_from_manifest(self, image_name: str, image_tag: str, manifest_path: str) -> None:
        """
        Syncs a single Docker image listed in a manifest from a source registry into the local registry.

        This is similar to sync_images_from_manifest(), but only processes the specified image.

        Args:
            image_name (str): Name of the image to sync (without registry).
            image_tag (str): Tag of the image to sync.
            manifest_path (str): Path to the manifest YAML file.

        Raises:
            KeywordException: If the image is not found in the manifest, if multiple entries are found,
                            or if the sync operation fails.
        """
        manifest = self._load_and_validate_manifest(manifest_path)
        target_image_entry = self._find_image_in_manifest(manifest, image_name, image_tag, manifest_path)

        self._sync_single_image_from_manifest(target_image_entry, manifest_path)
        get_logger().log_info(f"Successfully synced '{image_name}:{image_tag}' from manifest")

    def remove_image_from_manifest(self, image_name: str, image_tag: str, manifest_path: str) -> None:
        """
        Removes a single Docker image listed in a manifest from the local system.

        This is similar to remove_images_from_manifest(), but only processes the specified image.

        For each image, removal is attempted for:
        1. source_registry/image:tag   (skipped if source is docker.io; see note below)
        2. local_registry/image:tag
        3. image:tag

        Notes:
            - docker.io-prefixed references are skipped because Docker stores these as image:tag.
            - Removal is attempted even for images that were never successfully synced.

        Args:
            image_name (str): Name of the image to remove (without registry).
            image_tag (str): Tag of the image to remove.
            manifest_path (str): Path to the manifest YAML file.

        Raises:
            KeywordException: If the image is not found in the manifest, if multiple entries are found,
                            or if the removal operation fails.
        """
        manifest = self._load_and_validate_manifest(manifest_path)
        self._find_image_in_manifest(manifest, image_name, image_tag, manifest_path)

        refs = self._build_image_references_for_removal(image_name, image_tag, manifest_path)

        for ref in refs:
            self.docker_images_keywords.remove_image(ref)

        get_logger().log_info(f"Successfully removed '{image_name}:{image_tag}' from local Docker images.")

    def image_exists_in_local_registry(self, image_name: str, image_tag: str) -> bool:
        """
        Checks that a Docker image with the specified name and tag exists in the local registry.

        This is typically used after syncing a single image to confirm it was pushed successfully.

        Args:
            image_name (str): Name of the image to check (without registry prefix).
            image_tag (str): Tag of the image to check.

        Returns:
            bool: True if the image exists, False otherwise.
        """
        docker_config = ConfigurationManager.get_docker_config()
        local_registry = docker_config.get_registry("local_registry")
        local_registry_url = local_registry.get_registry_url()

        images = self.docker_images_keywords.list_images()

        expected_repo = f"{local_registry_url}/{image_name}"
        matches = [img for img in images if img.get_repository() == expected_repo and img.get_tag() == image_tag]

        if matches:
            get_logger().log_info(f"Image '{expected_repo}:{image_tag}' was found in the local registry.")
            return True
        else:
            get_logger().log_warning(f"Image '{expected_repo}:{image_tag}' was NOT found in the local registry.")
            return False
