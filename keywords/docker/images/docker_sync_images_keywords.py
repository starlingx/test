import os

import yaml

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.docker.images.docker_images_keywords import DockerImagesKeywords
from keywords.docker.images.docker_load_image_keywords import DockerLoadImageKeywords
from keywords.docker.login.docker_login_keywords import DockerLoginKeywords


class DockerSyncImagesKeywords(BaseKeyword):
    """
    Provides functionality for Docker image synchronization to local registry.

    This keyword provides manifest-based Docker image synchronization, allowing tests
    to pull images from public or private registries and push them to a local registry.

    Key Features:
    - Manifest-driven: Images are defined in YAML manifests with full registry paths
    - Flexible: Supports DockerHub, Quay, GCR, K8s registries, Harbor mirrors, and custom registries
    - Automatic authentication: Handles registry login based on configuration
    - Automatic normalization: Handles Docker's image name normalization (e.g., docker.io/busybox -> busybox)
    - Config-driven: Manifest paths can be resolved via configuration, enabling environment-specific image sources

    Manifest Format:
    - Images must be specified as tag-based references (image:tag)
    - Digest references (image@sha256:...) are not supported and will raise KeywordException

    Workflow:
    1. Pull image from source registry (specified in manifest)
    2. Tag image for local registry
    3. Push image to local registry
    4. Return local registry reference for use in tests
    """

    # Public registry patterns for canonical name extraction
    # These registries preserve namespace information (e.g., docker.io/calico/ctl -> calico/ctl)
    # Custom registry patterns are loaded from config and combined with these at runtime.
    PUBLIC_REGISTRY_PATTERNS = [
        "docker.io/",  # DockerHub
        "docker.io/library/",  # DockerHub official with explicit library
        "quay.io/",  # Quay
        "gcr.io/",  # Google Container Registry
        "ghcr.io/",  # GitHub Container Registry
        "registry.k8s.io/",  # Kubernetes registry
    ]

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Initialize DockerSyncImagesKeywords with an SSH connection.

        Args:
            ssh_connection (SSHConnection): Active SSH connection to the system under test.
        """
        self.ssh_connection = ssh_connection
        self.docker_images_keywords = DockerImagesKeywords(ssh_connection)
        self.docker_load_keywords = DockerLoadImageKeywords(ssh_connection)
        self.docker_config = ConfigurationManager.get_docker_config()

        # Build registry patterns for canonical name extraction
        # Start with public registry patterns (baseline)
        patterns = list(self.PUBLIC_REGISTRY_PATTERNS)

        if self.docker_config is not None:
            # Add custom registry patterns from config (for namespaced mirrors)
            custom_patterns = self.docker_config.get_custom_registry_patterns()
            for pattern in custom_patterns:
                # Ensure pattern ends with / for consistent matching
                normalized_pattern = pattern if pattern.endswith("/") else f"{pattern}/"
                if normalized_pattern not in patterns:
                    patterns.append(normalized_pattern)

        # Sort patterns by length (longest first) to ensure more specific patterns match first
        # This is critical for cases like "docker.io/library/" vs "docker.io/"
        # Without sorting: "docker.io/library/busybox" matches "docker.io/" -> "library/busybox" (wrong!)
        # With sorting: "docker.io/library/busybox" matches "docker.io/library/" -> "busybox" (correct!)
        self.registry_patterns = sorted(patterns, key=len, reverse=True)

    def get_registry_patterns(self) -> list:
        """Get the configured registry patterns for canonical name extraction.

        Returns:
            list: List of registry patterns (sorted longest first)
        """
        return self.registry_patterns

    def _resolve_manifest_path(self, manifest: str) -> str:
        """Resolve manifest name or path to file path.

        Supports both:
        1. Logical names from docker config JSON5 (e.g., "sanity", "harbor-prod")
        2. Direct file paths (absolute or relative) to manifest YAML files

        Args:
            manifest (str): Either a logical name from config or a file path

        Returns:
            str: Absolute path to manifest file

        Raises:
            KeywordException: If manifest cannot be resolved or file doesn't exist
        """
        # Try treating as direct file path first (absolute or relative)
        if os.path.isfile(manifest):
            return os.path.abspath(manifest)

        # Not a file path, try resolving as logical name from config
        try:
            path = self.docker_config.get_named_manifest(manifest)
            return os.path.abspath(path)
        except ValueError as e:
            raise KeywordException(f"Failed to resolve manifest '{manifest}': {e}. " "Provide either a logical name defined in docker config JSON5 or a valid file path.") from e

    def sync_image_from_manifest(self, image_name: str, image_tag: str, manifest: str) -> str:
        """
        Syncs a single Docker image from a manifest to the local registry.

        This is the primary API for tests. The manifest can be either a logical name from config
        or a direct path to a manifest YAML file. The manifest specifies full source registry paths
        for all images.

        The method searches the manifest for an image matching the provided name and tag,
        then extracts the canonical name from the found entry to ensure correct tagging.

        Args:
            image_name (str): Image name without registry prefix (e.g., "busybox", "calico/ctl", "myorg/myapp").
                            The manifest is searched for an image with this canonical name.
            image_tag (str): Image tag (e.g., "1.36.1", "v3.27.0")
            manifest (str): Either a logical name from docker config JSON5 (e.g., "sanity", "harbor-prod")
                          or a file path to a manifest YAML (e.g., "/path/to/custom-images.yaml")

        Returns:
            str: Local registry reference (e.g., "registry.local:9001/busybox:1.36.1")

        Raises:
            KeywordException: If manifest not found or image sync fails

        Example:
            >>> # Using logical name from config
            >>> sync_keywords.sync_image_from_manifest("busybox", "1.36.1", "sanity")
            "registry.local:9001/busybox:1.36.1"
            >>> # Namespace is preserved from manifest
            >>> sync_keywords.sync_image_from_manifest("myorg/myapp", "latest", "path/to/manifest.yaml")
            "registry.local:9001/myorg/myapp:latest"
        """
        # 1. Resolve manifest (logical name or file path)
        manifest_path = self._resolve_manifest_path(manifest)

        get_logger().log_info(f"Using manifest: {manifest_path}")

        # 2. Load manifest
        manifest_data = self._load_manifest(manifest_path)

        # 3. Find image in manifest
        full_image_ref = self._find_image_in_manifest(manifest_data, image_name, image_tag)

        if not full_image_ref:
            available_images = "\n  ".join(manifest_data.get("images", []))
            raise KeywordException(f"Image '{image_name}:{image_tag}' not found in manifest '{manifest_path}'.\n" f"Available images:\n  {available_images}")

        get_logger().log_info(f"Found image in manifest: {full_image_ref}")

        # 4. Extract canonical name from the found reference for consistent tagging
        ref_name, _ = self._parse_image_reference(full_image_ref)
        canonical_name = self._get_canonical_image_name(ref_name)

        # 5. Sync image (pull, tag, push)
        local_ref = self._sync_image(full_image_ref, canonical_name, image_tag)

        get_logger().log_info(f"Successfully synced image to: {local_ref}")
        return local_ref

    def sync_all_images_from_manifest(self, manifest: str) -> list[str]:
        """
        Syncs all images from a manifest to the local registry.

        Args:
            manifest (str): Either a logical name from docker config JSON5 (e.g., "sanity") or a file path to a manifest YAML

        Returns:
            list[str]: List of local registry references

        Raises:
            KeywordException: If manifest not found or any image sync fails
        """
        # Resolve manifest (logical name or file path)
        manifest_path = self._resolve_manifest_path(manifest)

        get_logger().log_info(f"Syncing all images from manifest: {manifest_path}")

        # Load manifest
        manifest = self._load_manifest(manifest_path)

        # Sync all images
        local_refs = []
        for full_image_ref in manifest.get("images", []):
            # Parse image name and tag from full reference
            ref_name, image_tag = self._parse_image_reference(full_image_ref)
            # Extract canonical name (without registry) for local tagging
            canonical_name = self._get_canonical_image_name(ref_name)

            try:
                local_ref = self._sync_image(full_image_ref, canonical_name, image_tag)
                local_refs.append(local_ref)
            except Exception as e:
                get_logger().log_error(f"Failed to sync {full_image_ref}: {e}")
                raise KeywordException(f"Image sync failed for {full_image_ref}: {e}") from e

        get_logger().log_info(f"Successfully synced {len(local_refs)} images")
        return local_refs

    def _load_manifest(self, manifest_path: str) -> dict:
        """
        Load and validate manifest file.

        Manifest images must be tag-based references (e.g., "image:tag").
        Digest references (e.g., "image@sha256:...") are rejected during parsing.

        Args:
            manifest_path (str): Path to manifest YAML file

        Returns:
            dict: Loaded manifest data

        Raises:
            KeywordException: If manifest cannot be loaded
        """
        try:
            with open(manifest_path, "r") as f:
                manifest = yaml.safe_load(f)
        except FileNotFoundError:
            raise KeywordException(f"Manifest file not found: {manifest_path}")
        except Exception as e:
            raise KeywordException(f"Failed to load manifest '{manifest_path}': {e}") from e

        if not manifest or "images" not in manifest:
            raise KeywordException(f"Manifest '{manifest_path}' is invalid or missing 'images' key")

        if not isinstance(manifest["images"], list):
            raise KeywordException(f"Manifest '{manifest_path}' 'images' must be a list")

        return manifest

    def _get_canonical_image_name(self, ref_name: str) -> str:
        """
        Extract the canonical image name from a full image reference.

        This is the "logical" image name used for matching and local registry tagging,
        with registry hostname stripped but namespace preserved.

        **Namespace Preservation:**
        Namespaces are ALWAYS preserved to avoid name collisions:
        - docker.io/calico/ctl -> calico/ctl
        - customregistry.io/project/myapp -> project/myapp
        - privateregistry.com:5000/team/tool -> team/tool

        For known registries (built-in public registries + custom patterns from config),
        the registry pattern is matched and stripped intelligently.

        For unknown registries (not in built-in patterns or config), only the registry
        hostname (first path component) is stripped, preserving the full namespace path.

        **Name Collision Prevention:**
        By preserving namespaces, images like "team-a/scanner" and "team-b/scanner"
        remain distinct and won't collide in manifests.

        Args:
            ref_name (str): Full image name without tag (e.g., "docker.io/busybox")

        Returns:
            str: Canonical image name without registry (e.g., "busybox", "calico/ctl", "project/myapp")

        Examples:
            >>> self._get_canonical_image_name("docker.io/library/busybox")
            "busybox"
            >>> self._get_canonical_image_name("docker.io/calico/ctl")
            "calico/ctl"
            >>> self._get_canonical_image_name("registry.k8s.io/pause")
            "pause"
            >>> self._get_canonical_image_name("harbor.local/project1/docker.io/calico/ctl")
            "calico/ctl"
            >>> self._get_canonical_image_name("customregistry.io/project/myapp")
            "project/myapp"
            >>> self._get_canonical_image_name("unknown.io/myorg/scanner")
            "myorg/scanner"
        """
        # Check for known registry patterns (public + custom from config)
        # Note: Using 'in' instead of 'startswith' allows Harbor mirrors like
        # "harbor.local/project1/docker.io/calico/ctl" to match the "docker.io/" pattern
        # and correctly extract "calico/ctl" instead of "project1/docker.io/calico/ctl"
        for pattern in self.registry_patterns:
            if pattern in ref_name:
                # Extract everything after this registry marker
                # This preserves namespace (e.g., docker.io/calico/ctl -> calico/ctl)
                return ref_name.split(pattern, 1)[1]

        # For unknown registries (not in public or custom patterns), preserve namespace to avoid collisions
        # Strip only the registry hostname (first path component)
        if "/" in ref_name:
            parts = ref_name.split("/", 1)
            if len(parts) > 1:
                # Return everything after first / (includes namespace)
                # e.g., unknown.registry.io/project/myapp -> project/myapp
                return parts[1]

        # No slashes - already canonical
        return ref_name

    def _find_image_in_manifest(self, manifest: dict, canonical_name: str, image_tag: str) -> str | None:
        """
        Find an image in manifest by canonical name and tag.

        Matches images where BOTH the canonical name and tag match exactly. Canonical names
        are extracted from full image references (e.g., "docker.io/busybox:1.36.1" -> "busybox").

        If multiple images have the same canonical name and tag (e.g., different source registries
        for the same image), the FIRST match is returned.

        Args:
            manifest (dict): Loaded manifest data
            canonical_name (str): Canonical image name without registry (e.g., "busybox", "calico/ctl", "myorg/myapp")
            image_tag (str): Image tag (e.g., "1.36.1")

        Returns:
            str | None: Full image reference (e.g., "docker.io/busybox:1.36.1") if found, None otherwise.
        """
        images = manifest.get("images", [])

        for full_ref in images:
            # Parse the full reference
            ref_name, ref_tag = self._parse_image_reference(full_ref)

            # Match on both name and tag
            # Tags must match exactly
            if ref_tag != image_tag:
                continue

            # Extract canonical image name and compare
            # This handles:
            #   - Public registries: docker.io/busybox -> busybox
            #   - Namespaced: docker.io/calico/ctl -> calico/ctl
            #   - Paths with known patterns: mirror.com/project/docker.io/busybox -> busybox
            #   - Unknown registries: custom.registry.io/project/myapp -> project/myapp
            extracted_canonical = self._get_canonical_image_name(ref_name)

            if extracted_canonical == canonical_name:
                return full_ref

        return None

    def _parse_image_reference(self, full_ref: str) -> tuple[str, str]:
        """
        Parse a full image reference into name and tag.

        Args:
            full_ref (str): Full image reference (e.g., "docker.io/busybox:1.36.1")

        Returns:
            tuple[str, str]: (image_name, image_tag)

        Raises:
            KeywordException: If reference is malformed (missing tag, contains digest, empty, etc.)

        Example:
            >>> _parse_image_reference("docker.io/busybox:1.36.1")
            ("docker.io/busybox", "1.36.1")
        """
        try:
            if not full_ref or not full_ref.strip():
                raise KeywordException("Image reference cannot be empty")

            if "@" in full_ref:
                raise KeywordException(f"Digest references are not supported: {full_ref}. " "Please use tag-based references (e.g., 'image:tag')")

            # Split on last colon to separate image name from tag
            # rsplit(":", 1) handles registry ports correctly:
            #   - "myregistry.io:5000/busybox:1.36.1" -> ["myregistry.io:5000/busybox", "1.36.1"]
            #   - "docker.io/busybox:1.36.1" -> ["docker.io/busybox", "1.36.1"]
            parts = full_ref.rsplit(":", 1)
            image_name = parts[0].strip()
            image_tag = parts[1].strip() if len(parts) > 1 else ""

            if not image_name:
                raise KeywordException(f"Invalid image reference (empty name): {full_ref}")

            if not image_tag:
                raise KeywordException(f"Invalid image reference (missing tag): {full_ref}")

            # Tags cannot contain '/' - if we see one, we split on the wrong colon (likely a registry port)
            # This catches cases like: "myregistry.io:5000/busybox" -> tag="5000/busybox"
            if "/" in image_tag:
                raise KeywordException(f"Invalid image reference (expected tag after last colon, found path separator): {full_ref}")

            return image_name, image_tag

        except KeywordException:
            raise
        except Exception as e:
            raise KeywordException(f"Failed to parse image reference '{full_ref}': {str(e)}") from e

    def _sync_image(self, full_image_ref: str, canonical_name: str, image_tag: str) -> str:
        """
        Sync a single image: pull from source, tag for local registry, push.

        This method includes automatic authentication for source registries.
        If the image's source registry is configured in docker config JSON5 source_registries,
        it will authenticate using the configured credentials before pulling.
        Public registries (not in source_registries) are accessed anonymously.

        Args:
            full_image_ref (str): Full image reference to pull (e.g., "docker.io/busybox:1.36.1")
            canonical_name (str): Canonical image name without registry (e.g., "busybox", "calico/ctl", "myorg/myapp")
            image_tag (str): Image tag (e.g., "1.36.1")

        Returns:
            str: Local registry reference

        Raises:
            KeywordException: If authentication, pull, tag, or push fails
        """
        local_registry = self.docker_config.get_local_registry()

        # Build destination image reference (preserves namespaces like "calico/ctl", "myorg/scanner")
        dest_image_with_tag = f"{canonical_name}:{image_tag}"
        local_ref = f"{local_registry.get_registry_url()}/{dest_image_with_tag}"

        try:
            # Check if we need to authenticate to source registry
            source_registry = self.docker_config.get_source_registry_for_image(full_image_ref)
            if source_registry:
                get_logger().log_info(f"Authenticating to source registry: {source_registry.get_registry_url()}")
                login_keywords = DockerLoginKeywords(self.ssh_connection)
                login_keywords.login(source_registry.get_user_name(), source_registry.get_password(), source_registry.get_registry_url())
                get_logger().log_info(f"Successfully authenticated to {source_registry.get_registry_url()}")

            # Pull from source
            get_logger().log_info(f"Pulling {full_image_ref}")
            self.docker_images_keywords.pull_image(full_image_ref)

            # Docker normalizes image names when pulling:
            # - docker.io/busybox:1.36.1 -> busybox:1.36.1
            # - docker.io/library/busybox:1.36.1 -> busybox:1.36.1
            # - registry.k8s.io/pause:3.9 -> registry.k8s.io/pause:3.9 (non-DockerHub stays as-is)
            # We need to tag from the normalized name Docker actually stored
            normalized_source = self._get_normalized_source_ref(full_image_ref)

            # Tag for local registry
            # Note: tag_docker_image_for_registry() has confusing parameter names:
            #   - image_name: actually the SOURCE image ref (what docker tag uses as source)
            #   - tag_name: actually the DEST name:tag (what goes after registry/)
            get_logger().log_info(f"Tagging {normalized_source} -> {local_ref}")
            self.docker_load_keywords.tag_docker_image_for_registry(image_name=normalized_source, tag_name=dest_image_with_tag, registry=local_registry)

            # Push to local registry
            get_logger().log_info(f"Pushing {local_ref}")
            self.docker_load_keywords.push_docker_image_to_registry(tag_name=dest_image_with_tag, registry=local_registry)

            return local_ref

        except Exception as e:
            raise KeywordException(f"Failed to sync image '{full_image_ref}': {e}") from e

    def _get_normalized_source_ref(self, full_image_ref: str) -> str:
        """
        Get the normalized image name that Docker uses when storing the image locally.

        Docker normalizes DockerHub images:
        - docker.io/busybox:1.36.1 -> busybox:1.36.1
        - docker.io/library/busybox:1.36.1 -> busybox:1.36.1
        - docker.io/calico/ctl:v3.27.0 -> calico/ctl:v3.27.0

        Non-DockerHub images keep full path:
        - registry.k8s.io/pause:3.9 -> registry.k8s.io/pause:3.9

        Args:
            full_image_ref (str): Full image reference (e.g., "docker.io/busybox:1.36.1")

        Returns:
            str: Normalized image name Docker uses locally
        """
        if not full_image_ref.startswith("docker.io/"):
            # Non-DockerHub registries keep their full path
            return full_image_ref

        # DockerHub image - strip docker.io/ prefix
        without_registry = full_image_ref[len("docker.io/") :]

        # Also strip "library/" for official images
        if without_registry.startswith("library/"):
            without_registry = without_registry[len("library/") :]

        return without_registry

    def remove_image_from_manifest(self, image_name: str, image_tag: str, manifest: str) -> None:
        """
        Remove an image from the local system using manifest reference.

        This handles cleanup of both:
        - The local registry copy (registry.local:9001/image:tag)
        - The source image copy (normalized Docker name)

        Like sync_image_from_manifest(), this method searches the manifest and extracts
        the canonical name from the found entry to ensure consistent cleanup.

        Args:
            image_name (str): Image name without registry prefix (e.g., "busybox", "calico/ctl", "myorg/myapp").
                            Must match the image name used when syncing.
            image_tag (str): Image tag (e.g., "1.36.1", "v3.27.0")
            manifest (str): Either a logical name from docker config JSON5 (e.g., "sanity")
                          or a file path to a manifest YAML

        Raises:
            KeywordException: If manifest not found or removal fails

        Example:
            >>> # After syncing busybox:
            >>> sync_keywords.sync_image_from_manifest("busybox", "1.36.1", "sanity")
            >>> # Clean it up (uses same search term):
            >>> sync_keywords.remove_image_from_manifest("busybox", "1.36.1", "sanity")
        """
        try:
            # Resolve manifest (logical name or file path)
            manifest_path = self._resolve_manifest_path(manifest)

            # Load manifest to get full source reference
            manifest_data = self._load_manifest(manifest_path)
            full_image_ref = self._find_image_in_manifest(manifest_data, image_name, image_tag)

            if not full_image_ref:
                get_logger().log_warning(f"Image '{image_name}:{image_tag}' not found in manifest '{manifest_path}', skipping removal")
                return

            # Extract canonical name from found reference (matches how we tagged during sync)
            ref_name, _ = self._parse_image_reference(full_image_ref)
            canonical_name = self._get_canonical_image_name(ref_name)

            # Get normalized source name (what Docker actually stored)
            normalized_source = self._get_normalized_source_ref(full_image_ref)

            # Build local registry reference using canonical name
            local_registry = self.docker_config.get_local_registry()
            local_ref = f"{local_registry.get_registry_url()}/{canonical_name}:{image_tag}"

            # Remove local registry copy
            get_logger().log_info(f"Removing local registry image: {local_ref}")
            self.docker_images_keywords.remove_image(local_ref)

            # Remove source copy (using normalized name)
            get_logger().log_info(f"Removing source image: {normalized_source}")
            self.docker_images_keywords.remove_image(normalized_source)

        except Exception as e:
            raise KeywordException(f"Failed to remove image '{image_name}:{image_tag}': {e}") from e

    def remove_images_from_manifest(self, manifest: str) -> None:
        """
        Removes all images from a manifest from the local system.

        Useful for cleanup after tests. Failures removing individual images are logged
        as warnings and do not stop processing of remaining images.

        Args:
            manifest (str): Either a logical name from docker config JSON5 (e.g., "sanity") or a file path to a manifest YAML

        Raises:
            KeywordException: If manifest not found
        """
        manifest_path = self._resolve_manifest_path(manifest)

        get_logger().log_info(f"Removing images from manifest: {manifest_path}")

        manifest = self._load_manifest(manifest_path)
        local_registry = self.docker_config.get_local_registry()

        for full_ref in manifest.get("images", []):
            ref_name, image_tag = self._parse_image_reference(full_ref)
            # Extract canonical name (matches how we tagged during sync)
            canonical_name = self._get_canonical_image_name(ref_name)

            # Build local registry reference
            local_ref = f"{local_registry.get_registry_url()}/{canonical_name}:{image_tag}"

            # Get normalized source name (what Docker actually stored)
            normalized_source = self._get_normalized_source_ref(full_ref)

            # Remove local registry copy
            try:
                get_logger().log_info(f"Removing local registry image: {local_ref}")
                self.docker_images_keywords.remove_image(local_ref)
            except Exception as e:
                get_logger().log_warning(f"Failed to remove local registry image {local_ref}: {e}")

            # Remove source copy
            try:
                get_logger().log_info(f"Removing source image: {normalized_source}")
                self.docker_images_keywords.remove_image(normalized_source)
            except Exception as e:
                get_logger().log_warning(f"Failed to remove source image {normalized_source}: {e}")
