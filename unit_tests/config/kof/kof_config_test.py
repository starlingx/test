"""Unit tests for KofConfig."""

import pytest

from config.kof.objects.kof_config import KofConfig


class TestKofConfigBasics:
    """Test basic KofConfig loading and validation."""

    def test_valid_minimal_config(self, tmp_path):
        """Verifies KofConfig loads with minimal required fields."""
        config_file = tmp_path / "kof_config.json5"
        config_file.write_text(
            """
        {
            "kmm_builder_image": "docker.io/starlingx/kmm-builder:stx.12.0-v1.0.0",
            "kmm_container_image_registry": "registry.local:9001/kmm/kmm-hello-world"
        }
        """
        )

        config = KofConfig(str(config_file))

        assert config.get_kmm_builder_image() == "docker.io/starlingx/kmm-builder:stx.12.0-v1.0.0"
        assert config.get_kmm_container_image_registry() == "registry.local:9001/kmm/kmm-hello-world"

    def test_missing_config_file_raises(self):
        """Verifies FileNotFoundError is raised for a nonexistent config file."""
        with pytest.raises(FileNotFoundError):
            KofConfig("nonexistent.json5")

    def test_custom_builder_and_container_image(self, tmp_path):
        """Verifies custom KMM builder image is loaded correctly."""
        config_file = tmp_path / "kof_config.json5"
        config_file.write_text(
            """
        {
            "kmm_builder_image": "custom.registry.io/kmm-builder:v2.0.0",
            "kmm_container_image_registry": "registry.local:9001/kmm/custom-module"
        }
        """
        )

        config = KofConfig(str(config_file))

        assert config.get_kmm_builder_image() == "custom.registry.io/kmm-builder:v2.0.0"
        assert config.get_kmm_container_image_registry() == "registry.local:9001/kmm/custom-module"
