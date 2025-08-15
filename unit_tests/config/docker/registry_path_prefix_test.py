from config.docker.objects.registry import Registry


class TestRegistryPathPrefix:
    """Tests for Registry path_prefix handling and URL construction."""

    def test_path_prefix_with_trailing_slash(self):
        """Test that path_prefix with trailing slash is returned as-is."""
        registry = Registry(registry_name="test_registry", registry_url="harbor.example.com", user_name="user", password="pass", path_prefix="project-x/test/")
        assert registry.get_path_prefix() == "project-x/test/"

    def test_path_prefix_without_trailing_slash(self):
        """Test that path_prefix without trailing slash is returned as-is."""
        registry = Registry(registry_name="test_registry", registry_url="harbor.example.com", user_name="user", password="pass", path_prefix="project-x/test")
        assert registry.get_path_prefix() == "project-x/test"

    def test_path_prefix_with_leading_slash(self):
        """Test that path_prefix with leading slash is returned as-is."""
        registry = Registry(registry_name="test_registry", registry_url="harbor.example.com", user_name="user", password="pass", path_prefix="/project-x/test/")
        assert registry.get_path_prefix() == "/project-x/test/"

    def test_empty_path_prefix(self):
        """Test that empty path_prefix returns empty string."""
        registry = Registry(registry_name="test_registry", registry_url="docker.io", user_name="user", password="pass", path_prefix="")
        assert registry.get_path_prefix() == ""

    def test_none_path_prefix(self):
        """Test that None path_prefix defaults to empty string."""
        registry = Registry(registry_name="test_registry", registry_url="docker.io", user_name="user", password="pass")
        assert registry.get_path_prefix() == ""

    def test_url_construction_normalization(self):
        """Test URL construction with various path_prefix formats."""
        test_cases = [
            ("project-x/test/", "harbor.com/project-x/test/busybox:1.0"),
            ("project-x/test", "harbor.com/project-x/test/busybox:1.0"),
            ("/project-x/test/", "harbor.com/project-x/test/busybox:1.0"),
            ("/project-x/test", "harbor.com/project-x/test/busybox:1.0"),
            ("", "harbor.com/busybox:1.0"),
        ]

        for path_prefix, expected_url in test_cases:
            registry = Registry(registry_name="test_registry", registry_url="harbor.com", user_name="user", password="pass", path_prefix=path_prefix)

            # Simulate the URL construction logic from the sync method
            registry_url = registry.get_registry_url()
            prefix = registry.get_path_prefix()
            if prefix:
                normalized_prefix = prefix.strip("/") + "/"
                actual_url = f"{registry_url}/{normalized_prefix}busybox:1.0"
            else:
                actual_url = f"{registry_url}/busybox:1.0"

            assert actual_url == expected_url, f"Failed for path_prefix='{path_prefix}'"
