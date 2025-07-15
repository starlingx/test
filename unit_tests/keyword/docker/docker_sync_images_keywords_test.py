from unittest.mock import Mock, mock_open, patch

import pytest
import yaml

from framework.exceptions.keyword_exception import KeywordException
from keywords.docker.images.docker_sync_images_keywords import DockerSyncImagesKeywords


class TestDockerSyncImagesKeywords:
    """Unit tests for DockerSyncImagesKeywords private helper methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ssh_connection = Mock()
        self.docker_sync_keywords = DockerSyncImagesKeywords(self.mock_ssh_connection)

    def test_load_and_validate_manifest_valid(self):
        """Test loading a valid manifest file."""
        manifest_content = {"images": [{"name": "busybox", "tag": "1.36.1"}, {"name": "alpine", "tag": "latest"}]}

        with patch("builtins.open", mock_open(read_data=yaml.dump(manifest_content))):
            with patch("yaml.safe_load", return_value=manifest_content):
                result = DockerSyncImagesKeywords._load_and_validate_manifest(self.docker_sync_keywords, "test_manifest.yaml")

                assert result == manifest_content
                assert "images" in result
                assert len(result["images"]) == 2

    def test_load_and_validate_manifest_missing_images_key(self):
        """Test loading a manifest without required 'images' key."""
        manifest_content = {"other_key": "value"}

        with patch("builtins.open", mock_open(read_data=yaml.dump(manifest_content))):
            with patch("yaml.safe_load", return_value=manifest_content):
                with pytest.raises(KeywordException, match="missing required 'images' key"):
                    DockerSyncImagesKeywords._load_and_validate_manifest(self.docker_sync_keywords, "test_manifest.yaml")

    def test_load_and_validate_manifest_file_not_found(self):
        """Test loading a non-existent manifest file."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(KeywordException, match="Failed to load manifest"):
                DockerSyncImagesKeywords._load_and_validate_manifest(self.docker_sync_keywords, "nonexistent.yaml")

    def test_find_image_in_manifest_single_match(self):
        """Test finding a single image in manifest."""
        manifest = {"images": [{"name": "busybox", "tag": "1.36.1"}, {"name": "alpine", "tag": "latest"}]}

        result = DockerSyncImagesKeywords._find_image_in_manifest(self.docker_sync_keywords, manifest, "busybox", "1.36.1", "test_manifest.yaml")

        assert result == {"name": "busybox", "tag": "1.36.1"}

    def test_find_image_in_manifest_not_found(self):
        """Test finding an image that doesn't exist in manifest."""
        manifest = {"images": [{"name": "busybox", "tag": "1.36.1"}]}

        with pytest.raises(KeywordException, match="Image 'nginx:latest' not found"):
            DockerSyncImagesKeywords._find_image_in_manifest(self.docker_sync_keywords, manifest, "nginx", "latest", "test_manifest.yaml")
