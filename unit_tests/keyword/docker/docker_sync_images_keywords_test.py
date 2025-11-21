"""Unit tests for DockerSyncImagesKeywords."""

from unittest.mock import Mock, mock_open, patch

import pytest
import yaml

from framework.exceptions.keyword_exception import KeywordException

# Mock the logger BEFORE importing the keyword class
with patch("framework.logging.automation_logger.get_logger") as _mock_get_logger:
    _mock_get_logger.return_value = Mock()
    from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords


class TestParseImageReference:
    """Test cases for _parse_image_reference() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_basic_image_with_tag(self):
        """Test parsing basic image:tag format."""
        name, tag = self.keywords._parse_image_reference("busybox:1.36.1")
        assert name == "busybox"
        assert tag == "1.36.1"

    def test_dockerhub_official_image(self):
        """Test parsing DockerHub official image."""
        name, tag = self.keywords._parse_image_reference("docker.io/busybox:1.36.1")
        assert name == "docker.io/busybox"
        assert tag == "1.36.1"

    def test_dockerhub_library_image(self):
        """Test parsing DockerHub library image."""
        name, tag = self.keywords._parse_image_reference("docker.io/library/busybox:1.36.1")
        assert name == "docker.io/library/busybox"
        assert tag == "1.36.1"

    def test_dockerhub_namespaced_image(self):
        """Test parsing DockerHub namespaced image."""
        name, tag = self.keywords._parse_image_reference("docker.io/calico/ctl:v3.27.0")
        assert name == "docker.io/calico/ctl"
        assert tag == "v3.27.0"

    def test_non_dockerhub_registry(self):
        """Test parsing image from non-DockerHub registry."""
        name, tag = self.keywords._parse_image_reference("registry.k8s.io/pause:3.9")
        assert name == "registry.k8s.io/pause"
        assert tag == "3.9"

    def test_registry_with_port(self):
        """Test parsing image from registry with port number."""
        name, tag = self.keywords._parse_image_reference("registry.local:5000/myimage:v1.0")
        assert name == "registry.local:5000/myimage"
        assert tag == "v1.0"

    def test_harbor_mirror_with_nested_path(self):
        """Test parsing Harbor mirror image with nested path."""
        name, tag = self.keywords._parse_image_reference("harbor.example.com:5000/project/mirror/docker.io/busybox:1.36.1")
        assert name == "harbor.example.com:5000/project/mirror/docker.io/busybox"
        assert tag == "1.36.1"

    def test_nested_namespace(self):
        """Test parsing image with nested namespace."""
        name, tag = self.keywords._parse_image_reference("gcr.io/project/subproject/image:tag")
        assert name == "gcr.io/project/subproject/image"
        assert tag == "tag"

    def test_tag_with_special_chars(self):
        """Test parsing tag with special characters."""
        name, tag = self.keywords._parse_image_reference("myimage:v1.0.0-alpha.1")
        assert name == "myimage"
        assert tag == "v1.0.0-alpha.1"

    def test_missing_tag_raises_exception(self):
        """Test that missing tag raises KeywordException."""
        with pytest.raises(KeywordException, match="Invalid image reference.*missing tag"):
            self.keywords._parse_image_reference("busybox")

    def test_missing_tag_with_registry_raises_exception(self):
        """Test that missing tag with registry raises KeywordException."""
        with pytest.raises(KeywordException, match="Invalid image reference.*missing tag"):
            self.keywords._parse_image_reference("docker.io/busybox")

    def test_registry_with_port_but_no_tag_raises_exception(self):
        """Test that registry:port/image without tag raises KeywordException."""
        with pytest.raises(KeywordException, match="Invalid image reference.*path separator"):
            self.keywords._parse_image_reference("registry.local:9001/busybox")

    def test_empty_string_raises_exception(self):
        """Test that empty string raises KeywordException."""
        with pytest.raises(KeywordException, match="Image reference cannot be empty"):
            self.keywords._parse_image_reference("")


class TestFindImageInManifest:
    """Test cases for _find_image_in_manifest() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_find_simple_image(self):
        """Test finding simple image in manifest."""
        manifest = {"images": ["docker.io/busybox:1.36.1", "docker.io/nginx:latest"]}
        result = self.keywords._find_image_in_manifest(manifest, "busybox", "1.36.1")
        assert result == "docker.io/busybox:1.36.1"

    def test_find_namespaced_image(self):
        """Test finding namespaced image in manifest."""
        manifest = {"images": ["docker.io/calico/ctl:v3.27.0", "docker.io/busybox:1.36.1"]}
        result = self.keywords._find_image_in_manifest(manifest, "calico/ctl", "v3.27.0")
        assert result == "docker.io/calico/ctl:v3.27.0"

    def test_find_non_dockerhub_image(self):
        """Test finding image from non-DockerHub registry."""
        manifest = {"images": ["registry.k8s.io/pause:3.9", "quay.io/prometheus/node-exporter:v1.0.0"]}
        result = self.keywords._find_image_in_manifest(manifest, "pause", "3.9")
        assert result == "registry.k8s.io/pause:3.9"

    def test_image_not_found_returns_none(self):
        """Test that non-existent image returns None."""
        manifest = {"images": ["docker.io/busybox:1.36.1"]}
        result = self.keywords._find_image_in_manifest(manifest, "nginx", "latest")
        assert result is None

    def test_wrong_tag_returns_none(self):
        """Test that wrong tag returns None."""
        manifest = {"images": ["docker.io/busybox:1.36.1"]}
        result = self.keywords._find_image_in_manifest(manifest, "busybox", "latest")
        assert result is None

    def test_no_substring_match_busy(self):
        """Test that substring 'busy' does not match 'busybox'."""
        manifest = {"images": ["docker.io/busybox:1.36.1"]}
        result = self.keywords._find_image_in_manifest(manifest, "busy", "1.36.1")
        assert result is None, "Should not match substring 'busy' in 'busybox'"

    def test_no_substring_match_box(self):
        """Test that substring 'box' does not match 'busybox'."""
        manifest = {"images": ["docker.io/busybox:1.36.1"]}
        result = self.keywords._find_image_in_manifest(manifest, "box", "1.36.1")
        assert result is None, "Should not match substring 'box' in 'busybox'"

    def test_no_partial_namespace_match(self):
        """Test that partial namespace does not match."""
        manifest = {"images": ["docker.io/calico/ctl:v3.27.0"]}
        # Should not match just "ctl" when full name is "calico/ctl"
        result = self.keywords._find_image_in_manifest(manifest, "ctl", "v3.27.0")
        assert result is None, "Should not match 'ctl' without namespace"

    def test_ambiguous_image_names(self):
        """Test behavior with ambiguous image names."""
        manifest = {"images": ["docker.io/myorg/test:1.0", "quay.io/otherorg/test:1.0"]}

        # Searching for just "test" should NOT match namespaced images
        # User must specify the full namespace to disambiguate
        result = self.keywords._find_image_in_manifest(manifest, "test", "1.0")
        assert result is None, "Should not match ambiguous 'test' without namespace"

        # But searching with namespace should work
        result = self.keywords._find_image_in_manifest(manifest, "myorg/test", "1.0")
        assert result == "docker.io/myorg/test:1.0"

        result = self.keywords._find_image_in_manifest(manifest, "otherorg/test", "1.0")
        assert result == "quay.io/otherorg/test:1.0"

    def test_empty_manifest(self):
        """Test with empty manifest."""
        manifest = {"images": []}
        result = self.keywords._find_image_in_manifest(manifest, "busybox", "1.36.1")
        assert result is None

    def test_custom_harbor_image(self):
        """Test finding custom Harbor images with namespace preservation."""
        # Custom Harbor format: harbor.com:port/project/image:tag
        # With namespace preservation, canonical names include the project (namespace)
        manifest = {"images": ["harbor.example.com:5000/myproject/custom-tool:latest", "harbor.example.com:5000/security/scanner:v1"]}

        # Should match with full namespace (project/image)
        result = self.keywords._find_image_in_manifest(manifest, "myproject/custom-tool", "latest")
        assert result == "harbor.example.com:5000/myproject/custom-tool:latest"

        result = self.keywords._find_image_in_manifest(manifest, "security/scanner", "v1")
        assert result == "harbor.example.com:5000/security/scanner:v1"

        # Should NOT match without namespace (prevents ambiguity)
        result = self.keywords._find_image_in_manifest(manifest, "custom-tool", "latest")
        assert result is None

        result = self.keywords._find_image_in_manifest(manifest, "scanner", "v1")
        assert result is None


class TestGetNormalizedImageName:
    """Test cases for _get_normalized_image_name() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_dockerhub_official_image(self):
        """Test DockerHub official image normalization."""
        assert self.keywords._get_normalized_source_ref("docker.io/busybox:1.36.1") == "busybox:1.36.1"

    def test_dockerhub_library_image(self):
        """Test DockerHub library image normalization."""
        assert self.keywords._get_normalized_source_ref("docker.io/library/busybox:1.36.1") == "busybox:1.36.1"

    def test_dockerhub_namespaced_image(self):
        """Test DockerHub namespaced image normalization."""
        assert self.keywords._get_normalized_source_ref("docker.io/calico/ctl:v3.27.0") == "calico/ctl:v3.27.0"

    def test_dockerhub_nested_namespace(self):
        """Test DockerHub image with nested namespace."""
        assert self.keywords._get_normalized_source_ref("docker.io/org/project/image:tag") == "org/project/image:tag"

    def test_non_dockerhub_unchanged(self):
        """Test non-DockerHub registry stays unchanged."""
        assert self.keywords._get_normalized_source_ref("registry.k8s.io/pause:3.9") == "registry.k8s.io/pause:3.9"

    def test_quay_io_unchanged(self):
        """Test Quay.io image stays unchanged."""
        assert self.keywords._get_normalized_source_ref("quay.io/prometheus/node-exporter:v1.0.0") == "quay.io/prometheus/node-exporter:v1.0.0"

    def test_gcr_io_unchanged(self):
        """Test GCR image stays unchanged."""
        assert self.keywords._get_normalized_source_ref("gcr.io/project/image:tag") == "gcr.io/project/image:tag"

    def test_harbor_mirror_unchanged(self):
        """Test Harbor mirror path stays unchanged."""
        assert self.keywords._get_normalized_source_ref("harbor.example.com:5000/project/mirror/docker.io/busybox:1.36.1") == "harbor.example.com:5000/project/mirror/docker.io/busybox:1.36.1"

    def test_local_registry_unchanged(self):
        """Test local registry with port stays unchanged."""
        assert self.keywords._get_normalized_source_ref("registry.local:9001/busybox:1.36.1") == "registry.local:9001/busybox:1.36.1"


class TestGetCanonicalImageName:
    """Test cases for _get_canonical_image_name() method - namespace preservation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_dockerhub_official_strips_registry_and_library(self):
        """Test DockerHub official image strips docker.io/library/."""
        assert self.keywords._get_canonical_image_name("docker.io/library/busybox") == "busybox"

    def test_dockerhub_strips_registry_preserves_namespace(self):
        """Test DockerHub strips docker.io/ but preserves namespace."""
        assert self.keywords._get_canonical_image_name("docker.io/calico/ctl") == "calico/ctl"

    def test_dockerhub_nested_namespace_preserved(self):
        """Test DockerHub with nested namespace preserves all namespace parts."""
        assert self.keywords._get_canonical_image_name("docker.io/org/project/image") == "org/project/image"

    def test_known_registry_preserves_namespace(self):
        """Test known registries (quay, k8s, gcr) preserve namespace."""
        assert self.keywords._get_canonical_image_name("quay.io/prometheus/node-exporter") == "prometheus/node-exporter"
        assert self.keywords._get_canonical_image_name("registry.k8s.io/coredns/coredns") == "coredns/coredns"
        assert self.keywords._get_canonical_image_name("gcr.io/project/subproject/image") == "project/subproject/image"

    def test_unknown_registry_preserves_namespace(self):
        """Test unknown registries preserve namespace to avoid collisions."""
        # Unknown registry - should preserve full namespace path
        assert self.keywords._get_canonical_image_name("unknown.registry.io/project/myapp") == "project/myapp"
        assert self.keywords._get_canonical_image_name("private.company.com/team/tool") == "team/tool"

    def test_unknown_registry_with_port_preserves_namespace(self):
        """Test unknown registry with port preserves namespace."""
        assert self.keywords._get_canonical_image_name("unknown.registry.io:5000/project/myapp") == "project/myapp"
        assert self.keywords._get_canonical_image_name("custom.reg:9001/akantek/scanner") == "akantek/scanner"

    def test_unknown_registry_nested_namespace(self):
        """Test unknown registry with deeply nested namespace."""
        assert self.keywords._get_canonical_image_name("unknown.io/org/team/project/app") == "org/team/project/app"

    def test_no_collision_between_different_namespaces(self):
        """Test that images with same basename but different namespaces don't collide."""
        # These should produce DIFFERENT canonical names
        canonical1 = self.keywords._get_canonical_image_name("unknown.io/akantek/scanner")
        canonical2 = self.keywords._get_canonical_image_name("unknown.io/cve-tools/scanner")

        assert canonical1 == "akantek/scanner"
        assert canonical2 == "cve-tools/scanner"
        assert canonical1 != canonical2, "Different namespaces should produce different canonical names"

    def test_simple_image_no_registry(self):
        """Test image without registry or namespace (edge case - shouldn't happen in practice)."""
        assert self.keywords._get_canonical_image_name("busybox") == "busybox"


class TestLoadManifest:
    """Test cases for _load_manifest() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_load_valid_manifest(self):
        """Test loading valid manifest file."""
        manifest_content = {"images": ["docker.io/busybox:1.36.1", "docker.io/nginx:latest"]}

        with patch("builtins.open", mock_open(read_data=yaml.dump(manifest_content))):
            result = self.keywords._load_manifest("/path/to/manifest.yaml")
            assert result == manifest_content
            assert "images" in result
            assert len(result["images"]) == 2

    def test_manifest_file_not_found(self):
        """Test loading non-existent manifest file."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with pytest.raises(KeywordException, match="Manifest file not found"):
                self.keywords._load_manifest("/nonexistent/manifest.yaml")

    def test_manifest_missing_images_key(self):
        """Test manifest without 'images' key."""
        manifest_content = {"other_key": "value"}

        with patch("builtins.open", mock_open(read_data=yaml.dump(manifest_content))):
            with pytest.raises(KeywordException, match="invalid or missing 'images' key"):
                self.keywords._load_manifest("/path/to/manifest.yaml")

    def test_manifest_images_not_list(self):
        """Test manifest with 'images' as non-list."""
        manifest_content = {"images": "not a list"}

        with patch("builtins.open", mock_open(read_data=yaml.dump(manifest_content))):
            with pytest.raises(KeywordException, match="'images' must be a list"):
                self.keywords._load_manifest("/path/to/manifest.yaml")

    def test_manifest_invalid_yaml(self):
        """Test manifest with invalid YAML."""
        with patch("builtins.open", mock_open(read_data="invalid: yaml: content:")):
            with patch("yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML")):
                with pytest.raises(KeywordException, match="Failed to load manifest"):
                    self.keywords._load_manifest("/path/to/manifest.yaml")


class TestEdgeCases:
    """Test cases for edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_parse_image_with_multiple_colons(self):
        """Test parsing image reference with multiple colons in registry."""
        # Registry with port has colon, plus tag has colon
        name, tag = self.keywords._parse_image_reference("registry.local:5000/myimage:v1.0")
        assert name == "registry.local:5000/myimage"
        assert tag == "v1.0"

    def test_parse_image_with_sha256_digest(self):
        """Test parsing image with SHA256 digest (should fail as we expect tag)."""
        # Our implementation expects tags, not digests
        # This documents current behavior - may need enhancement for digest support
        with pytest.raises(KeywordException):
            self.keywords._parse_image_reference("busybox@sha256:abcdef123456")

    def test_normalize_already_normalized_image(self):
        """Test normalizing an already normalized image."""
        # If Docker already normalized it, normalizing again should be idempotent
        assert self.keywords._get_normalized_source_ref("busybox:1.36.1") == "busybox:1.36.1"
        assert self.keywords._get_normalized_source_ref("calico/ctl:v3.27.0") == "calico/ctl:v3.27.0"

    def test_find_image_with_similar_names(self):
        """Test finding image when manifest has similar names."""
        manifest = {"images": ["docker.io/busybox:1.36.1", "docker.io/busybox-extras:1.36.1", "quay.io/busybox:1.36.1"]}

        # Should find exact match, not substring
        result = self.keywords._find_image_in_manifest(manifest, "busybox", "1.36.1")
        assert result == "docker.io/busybox:1.36.1"

        # Should not match busybox-extras
        result = self.keywords._find_image_in_manifest(manifest, "busybox-extras", "1.36.1")
        assert result == "docker.io/busybox-extras:1.36.1"


class TestDocumentation:
    """Test cases that serve as documentation for expected behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_dockerhub_normalization_examples(self):
        """Document DockerHub normalization rules with examples."""
        # Official images (library)
        assert self.keywords._get_normalized_source_ref("docker.io/library/busybox:1.36.1") == "busybox:1.36.1"
        assert self.keywords._get_normalized_source_ref("docker.io/library/nginx:latest") == "nginx:latest"

        # DockerHub implicit library
        assert self.keywords._get_normalized_source_ref("docker.io/busybox:1.36.1") == "busybox:1.36.1"

        # DockerHub with namespace
        assert self.keywords._get_normalized_source_ref("docker.io/calico/ctl:v3.27.0") == "calico/ctl:v3.27.0"
        assert self.keywords._get_normalized_source_ref("docker.io/bitnami/nginx:1.0") == "bitnami/nginx:1.0"

    def test_non_dockerhub_examples(self):
        """Document non-DockerHub registry behavior with examples."""
        # Kubernetes registry
        assert self.keywords._get_normalized_source_ref("registry.k8s.io/pause:3.9") == "registry.k8s.io/pause:3.9"

        # Quay.io
        assert self.keywords._get_normalized_source_ref("quay.io/prometheus/node-exporter:v1.0.0") == "quay.io/prometheus/node-exporter:v1.0.0"

        # Google Container Registry
        assert self.keywords._get_normalized_source_ref("gcr.io/project/image:tag") == "gcr.io/project/image:tag"

        # Harbor mirror
        assert self.keywords._get_normalized_source_ref("harbor.example.com/library/busybox:1.36.1") == "harbor.example.com/library/busybox:1.36.1"

    def test_image_reference_format_examples(self):
        """Document expected image reference formats with examples."""
        # Basic format
        name, tag = self.keywords._parse_image_reference("busybox:1.36.1")
        assert name == "busybox" and tag == "1.36.1"

        # With registry
        name, tag = self.keywords._parse_image_reference("docker.io/busybox:1.36.1")
        assert name == "docker.io/busybox" and tag == "1.36.1"

        # With namespace
        name, tag = self.keywords._parse_image_reference("docker.io/calico/ctl:v3.27.0")
        assert name == "docker.io/calico/ctl" and tag == "v3.27.0"

        # With registry and port
        name, tag = self.keywords._parse_image_reference("registry.local:5000/image:tag")
        assert name == "registry.local:5000/image" and tag == "tag"


class TestCustomRegistryPatterns:
    """Test cases for custom registry patterns loading and usage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        # Setup with no docker config (default case)
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_patterns_sorted_by_length_longest_first(self):
        """Test that patterns are sorted by length (longest first) for correct matching."""
        # Find positions of docker.io patterns
        patterns = self.keywords.get_registry_patterns()
        docker_io_idx = patterns.index("docker.io/")
        docker_io_library_idx = patterns.index("docker.io/library/")

        # Longer pattern (docker.io/library/) should come before shorter (docker.io/)
        assert docker_io_library_idx < docker_io_idx, "docker.io/library/ should come before docker.io/ to match more specific patterns first"

    def test_no_config_falls_back_to_public_patterns_only(self):
        """Test that when config is None, only public patterns are used."""
        # Should only have public patterns
        patterns = self.keywords.get_registry_patterns()
        assert "docker.io/" in patterns
        assert "docker.io/library/" in patterns
        assert "quay.io/" in patterns
        assert "gcr.io/" in patterns
        assert "registry.k8s.io/" in patterns

        # Should still work for extracting canonical names
        assert self.keywords._get_canonical_image_name("docker.io/library/busybox") == "busybox"
        assert self.keywords._get_canonical_image_name("quay.io/prometheus/node-exporter") == "prometheus/node-exporter"

    def test_dockerhub_library_uses_longest_pattern_match(self):
        """Test that docker.io/library/ matches before docker.io/ due to sorting."""
        # This is the critical test - without sorting, this would return "library/busybox"
        result = self.keywords._get_canonical_image_name("docker.io/library/busybox")
        assert result == "busybox", "docker.io/library/ pattern should match before docker.io/"

    def test_harbor_mirror_with_dockerio_prefix(self):
        """Test Harbor mirror URLs that contain docker.io in the path."""
        # Even though this contains "docker.io/", since harbor.local isn't in patterns,
        # it should strip only the registry hostname (first part before /)
        result = self.keywords._get_canonical_image_name("harbor.local/project/docker.io/busybox")

        # Since "docker.io/" is in the string, it will match and split on that
        # This is the desired behavior for Harbor mirrors
        assert result == "busybox"


class TestHarborMirrorSupport:
    """Test cases for Harbor mirror URL patterns with embedded registry paths."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_harbor_simple_dockerhub_mirror(self):
        """Test Harbor mirror with simple DockerHub image (busybox)."""
        # Harbor URL: harbor.example.com:5000/library/mirror/docker.io/busybox
        result = self.keywords._get_canonical_image_name("harbor.example.com:5000/library/mirror/docker.io/busybox")
        assert result == "busybox", "Harbor mirror should find embedded docker.io/ and extract busybox"

    def test_harbor_dockerhub_namespaced_mirror(self):
        """Test Harbor mirror with namespaced DockerHub image."""
        # Harbor URL: harbor.example.com:5000/library/mirror/docker.io/calico/ctl
        result = self.keywords._get_canonical_image_name("harbor.example.com:5000/library/mirror/docker.io/calico/ctl")
        assert result == "calico/ctl", "Harbor mirror should preserve namespace from embedded docker.io/ path"

    def test_harbor_quay_mirror(self):
        """Test Harbor mirror with Quay.io image."""
        # Harbor URL: harbor.example.com:5000/library/mirror/quay.io/prometheus/node-exporter
        result = self.keywords._get_canonical_image_name("harbor.example.com:5000/library/mirror/quay.io/prometheus/node-exporter")
        assert result == "prometheus/node-exporter", "Harbor mirror should find embedded quay.io/ pattern"

    def test_harbor_gcr_mirror(self):
        """Test Harbor mirror with GCR image."""
        # Harbor URL: harbor.local/mirror/gcr.io/project/image
        result = self.keywords._get_canonical_image_name("harbor.local/mirror/gcr.io/project/image")
        assert result == "project/image", "Harbor mirror should find embedded gcr.io/ pattern"

    def test_harbor_k8s_registry_mirror(self):
        """Test Harbor mirror with Kubernetes registry image."""
        # Harbor URL: harbor.local/k8s-mirror/registry.k8s.io/pause
        result = self.keywords._get_canonical_image_name("harbor.local/k8s-mirror/registry.k8s.io/pause")
        assert result == "pause", "Harbor mirror should find embedded registry.k8s.io/ pattern"

    def test_harbor_dockerhub_library_mirror(self):
        """Test Harbor mirror with DockerHub library image (explicit library path)."""
        # Harbor URL: harbor.example.com:5000/library/mirror/docker.io/library/busybox
        result = self.keywords._get_canonical_image_name("harbor.example.com:5000/library/mirror/docker.io/library/busybox")
        assert result == "busybox", "Harbor mirror should match docker.io/library/ (longest pattern first)"

    def test_harbor_custom_namespace_without_embedded_registry(self):
        """Test Harbor custom project that doesn't mirror public registries."""
        # Harbor custom project: harbor.example.com:5000/myorg/custom-tool
        # This doesn't contain docker.io/ or other public registry patterns
        result = self.keywords._get_canonical_image_name("harbor.example.com:5000/myorg/custom-tool")
        assert result == "myorg/custom-tool", "Harbor custom project should preserve namespace via fallback logic"

    def test_harbor_deeply_nested_mirror_path(self):
        """Test Harbor mirror with multiple path components before embedded registry."""
        # Harbor URL: harbor.example.com:5000/org/team/project/docker.io/app
        result = self.keywords._get_canonical_image_name("harbor.example.com:5000/org/team/project/docker.io/app")
        assert result == "app", "Should find embedded docker.io/ regardless of path depth"

    def test_harbor_vs_standard_registry_same_image(self):
        """Test that Harbor mirror and standard registry extract same canonical name."""
        # Standard DockerHub reference
        canonical_standard = self.keywords._get_canonical_image_name("docker.io/busybox")

        # Harbor mirror of same image
        canonical_harbor = self.keywords._get_canonical_image_name("harbor.example.com:5000/library/mirror/docker.io/busybox")

        assert canonical_standard == canonical_harbor == "busybox", "Both should extract same canonical name"


class TestNamespacedMirrorArchitectures:
    """Test cases for mirrors organized by project/team (not by source registry)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_flat_mirror_no_namespace(self):
        """Test flat mirror structure without project namespaces."""
        # Flat mirror: mirror.corporate.io:5000/busybox
        result = self.keywords._get_canonical_image_name("mirror.corporate.io:5000/busybox")
        assert result == "busybox", "Flat mirror should work via fallback (strip first component)"

    def test_flat_mirror_with_image_namespace(self):
        """Test flat mirror with namespaced image."""
        # Flat mirror: mirror.corporate.io:5000/calico/ctl
        result = self.keywords._get_canonical_image_name("mirror.corporate.io:5000/calico/ctl")
        assert result == "calico/ctl", "Flat mirror should preserve image namespace"

    def test_namespaced_mirror_without_custom_pattern(self):
        """Test namespaced mirror WITHOUT custom_registry_patterns (documents limitation)."""
        # Namespaced mirror: mirror.corporate.io:5000/stx-images/busybox
        # WITHOUT custom pattern, this would incorrectly include project namespace
        result = self.keywords._get_canonical_image_name("mirror.corporate.io:5000/stx-images/busybox")
        assert result == "stx-images/busybox", "Without custom pattern, project namespace is included (incorrect)"
        # This documents the need for custom_registry_patterns for this architecture

    def test_multiple_project_namespaces_collision_risk(self):
        """Test that namespaced mirrors risk collisions without custom patterns."""
        # Two different projects with same image name
        result1 = self.keywords._get_canonical_image_name("mirror.corp.io:5000/stx-images/busybox")
        result2 = self.keywords._get_canonical_image_name("mirror.corp.io:5000/k8s-images/busybox")

        # Without custom patterns, both produce different names (includes project)
        assert result1 == "stx-images/busybox"
        assert result2 == "k8s-images/busybox"
        assert result1 != result2
        # This is actually INCORRECT behavior - both should be "busybox"
        # This documents why custom_registry_patterns is needed


class TestPatternMatchingBehavior:
    """Test cases documenting pattern matching behavior and edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_substring_match_enables_harbor_support(self):
        """Test that 'in' operator (substring match) enables Harbor mirror support."""
        # Using 'in' operator allows finding embedded patterns
        test_url = "harbor.local/project/docker.io/busybox"

        # Verify docker.io/ is found as substring (not prefix)
        assert "docker.io/" in test_url
        assert not test_url.startswith("docker.io/")

        # Extraction should work
        result = self.keywords._get_canonical_image_name(test_url)
        assert result == "busybox"

    def test_pattern_sorting_prevents_incorrect_matches(self):
        """Test that longest-first sorting prevents shorter patterns from matching first."""
        # Test that docker.io/library/ matches before docker.io/
        patterns = self.keywords.get_registry_patterns()
        library_idx = patterns.index("docker.io/library/")
        dockerio_idx = patterns.index("docker.io/")

        assert library_idx < dockerio_idx, "Longer pattern must be checked first"

        # Verify correct extraction for library image
        result = self.keywords._get_canonical_image_name("docker.io/library/nginx")
        assert result == "nginx", "Should match docker.io/library/ not docker.io/"

    def test_fallback_strips_only_hostname(self):
        """Test that fallback logic strips only registry hostname (first component)."""
        # Unknown registry without matching pattern
        result = self.keywords._get_canonical_image_name("unknown.registry.io/project/app")
        assert result == "project/app", "Should strip only unknown.registry.io, preserve project/app"

        result = self.keywords._get_canonical_image_name("private.corp.com:5000/team/tool")
        assert result == "team/tool", "Should strip registry:port, preserve namespace"

    def test_no_slashes_returns_as_is(self):
        """Test that image name without slashes is returned unchanged."""
        result = self.keywords._get_canonical_image_name("busybox")
        assert result == "busybox", "Simple name without registry should return as-is"

    def test_pattern_match_is_first_occurrence(self):
        """Test that split happens on first occurrence of pattern."""
        # URL with pattern appearing multiple times (edge case)
        # Example: mirror.io/docker.io-backup/docker.io/busybox
        result = self.keywords._get_canonical_image_name("mirror.io/docker.io-backup/docker.io/busybox")
        # Should split on FIRST occurrence of "docker.io/"
        # "mirror.io/docker.io-backup/docker.io/busybox".split("docker.io/", 1)
        # -> ["mirror.io/", "busybox"]  (because split(maxsplit=1) stops after first split)

        # Actually, with 'in' check, it will find "docker.io/" and split on first occurrence
        # split("docker.io/", 1) splits on first match: ["mirror.io/docker.io-backup/", "busybox"]
        assert result == "busybox", "Should split on first occurrence of pattern"


class TestNamespaceCollisionPrevention:
    """Test cases documenting namespace preservation for collision prevention."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_different_namespaces_produce_different_canonical_names(self):
        """Test that same image name in different namespaces produces different canonical names."""
        canon1 = self.keywords._get_canonical_image_name("docker.io/team-a/scanner")
        canon2 = self.keywords._get_canonical_image_name("docker.io/team-b/scanner")
        canon3 = self.keywords._get_canonical_image_name("quay.io/security/scanner")

        assert canon1 == "team-a/scanner"
        assert canon2 == "team-b/scanner"
        assert canon3 == "security/scanner"

        # All different - no collisions
        assert len({canon1, canon2, canon3}) == 3, "All three should be unique"

    def test_namespace_preserved_across_registries(self):
        """Test that namespace is preserved regardless of source registry."""
        # Same namespace/image from different registries should produce same canonical name
        canon1 = self.keywords._get_canonical_image_name("docker.io/calico/ctl")
        canon2 = self.keywords._get_canonical_image_name("quay.io/calico/ctl")
        canon3 = self.keywords._get_canonical_image_name("gcr.io/calico/ctl")

        assert canon1 == canon2 == canon3 == "calico/ctl"

    def test_deeply_nested_namespace_preserved(self):
        """Test that deeply nested namespaces are fully preserved."""
        result = self.keywords._get_canonical_image_name("docker.io/org/team/project/component")
        assert result == "org/team/project/component", "All namespace levels should be preserved"

        result = self.keywords._get_canonical_image_name("unknown.io/level1/level2/level3/app")
        assert result == "level1/level2/level3/app", "Deep nesting preserved for unknown registries"

    def test_official_images_no_namespace(self):
        """Test that official images correctly have no namespace."""
        # Official DockerHub images should have NO namespace in canonical name
        assert self.keywords._get_canonical_image_name("docker.io/busybox") == "busybox"
        assert self.keywords._get_canonical_image_name("docker.io/library/nginx") == "nginx"
        assert self.keywords._get_canonical_image_name("docker.io/library/redis") == "redis"


class TestManifestSearchExactMatching:
    """Test cases for exact matching behavior in _find_image_in_manifest()."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh = Mock()
        self.keywords = DockerSyncImagesKeywords(self.mock_ssh)

    def test_no_partial_matches_busybox_vs_busybox_extras(self):
        """Test that busybox doesn't match busybox-extras."""
        manifest = {
            "images": [
                "docker.io/busybox:1.36.1",
                "docker.io/busybox-extras:1.36.1",
            ]
        }

        result = self.keywords._find_image_in_manifest(manifest, "busybox", "1.36.1")
        assert result == "docker.io/busybox:1.36.1"

        result = self.keywords._find_image_in_manifest(manifest, "busybox-extras", "1.36.1")
        assert result == "docker.io/busybox-extras:1.36.1"

    def test_namespace_required_for_namespaced_images(self):
        """Test that namespace must be included for namespaced images."""
        manifest = {
            "images": [
                "docker.io/myorg/test:1.0",
                "docker.io/otherorg/test:1.0",
            ]
        }

        # Searching for just "test" should NOT match
        result = self.keywords._find_image_in_manifest(manifest, "test", "1.0")
        assert result is None, "Should require full namespace"

        # Must include namespace
        result = self.keywords._find_image_in_manifest(manifest, "myorg/test", "1.0")
        assert result == "docker.io/myorg/test:1.0"

    def test_harbor_mirror_and_public_same_canonical_name(self):
        """Test finding image when manifest has both Harbor mirror and public version."""
        manifest = {
            "images": [
                "docker.io/busybox:1.36.1",  # Public
                "harbor.example.com:5000/library/mirror/docker.io/busybox:1.36.1",  # Harbor
            ]
        }

        # Searching for "busybox" should match FIRST occurrence
        result = self.keywords._find_image_in_manifest(manifest, "busybox", "1.36.1")
        assert result == "docker.io/busybox:1.36.1", "Should return first match"

    def test_tag_must_match_exactly(self):
        """Test that tags must match exactly (no partial matching)."""
        manifest = {
            "images": [
                "docker.io/myapp:v1.0.0",
                "docker.io/myapp:v1.0.0-alpha",
                "docker.io/myapp:v1.0.1",
            ]
        }

        result = self.keywords._find_image_in_manifest(manifest, "myapp", "v1.0.0")
        assert result == "docker.io/myapp:v1.0.0", "Should match exact tag"

        result = self.keywords._find_image_in_manifest(manifest, "myapp", "v1.0")
        assert result is None, "Should not match partial tag"
