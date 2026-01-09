"""
Unit tests for YamlKeywords class.

Tests the read_yaml_file_as_string() method added per ADR-2026-01-09.
"""

import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

from keywords.files.yaml_keywords import YamlKeywords


class TestYamlKeywords(unittest.TestCase):
    """Test suite for YamlKeywords class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_ssh_connection = Mock()
        # Mock the logger to avoid configuration requirement
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.mock_logger = self.logger_patcher.start()
        self.yaml_keywords = YamlKeywords(self.mock_ssh_connection)
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        # Stop the logger patcher
        self.logger_patcher.stop()
        # Clean up any temporary files
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_read_yaml_file_as_string_valid(self):
        """Test reading valid YAML file returns string."""
        # Create a valid YAML file
        yaml_content = """apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
"""
        yaml_file = os.path.join(self.temp_dir, "valid.yaml")
        with open(yaml_file, "w") as f:
            f.write(yaml_content)

        # Read the file as string
        result = self.yaml_keywords.read_yaml_file_as_string(yaml_file)

        # Verify it returns a string
        self.assertIsInstance(result, str)
        # Verify content matches
        self.assertEqual(result, yaml_content)

    def test_read_yaml_file_as_string_preserves_formatting(self):
        """Test returned string matches original file content exactly."""
        # Create YAML with specific formatting, comments, and whitespace
        yaml_content = """# This is a comment
apiVersion: v1
kind: ConfigMap

metadata:
  name: my-config  # inline comment
  labels:
    app: test

data:
  key1: value1
  key2: |
    multi-line
    value
"""
        yaml_file = os.path.join(self.temp_dir, "formatted.yaml")
        with open(yaml_file, "w") as f:
            f.write(yaml_content)

        # Read the file
        result = self.yaml_keywords.read_yaml_file_as_string(yaml_file)

        # Verify exact match (including comments and formatting)
        self.assertEqual(result, yaml_content)

    def test_read_yaml_file_as_string_invalid_syntax(self):
        """Test reading invalid YAML raises yaml.YAMLError."""
        # Create an invalid YAML file (mismatched indentation)
        invalid_yaml = """apiVersion: v1
kind: Pod
metadata:
name: test-pod  # Wrong indentation
  labels:
    app: test
"""
        yaml_file = os.path.join(self.temp_dir, "invalid.yaml")
        with open(yaml_file, "w") as f:
            f.write(invalid_yaml)

        # Attempt to read the file
        with self.assertRaises(yaml.YAMLError) as context:
            self.yaml_keywords.read_yaml_file_as_string(yaml_file)

        # Verify error message contains file path
        self.assertIn(yaml_file, str(context.exception))

    def test_read_yaml_file_as_string_missing_file(self):
        """Test reading nonexistent file raises FileNotFoundError."""
        nonexistent_file = os.path.join(self.temp_dir, "does_not_exist.yaml")

        # Attempt to read nonexistent file
        with self.assertRaises(FileNotFoundError):
            self.yaml_keywords.read_yaml_file_as_string(nonexistent_file)

    def test_read_yaml_file_as_string_empty_file(self):
        """Test reading empty YAML file returns empty string."""
        yaml_file = os.path.join(self.temp_dir, "empty.yaml")
        with open(yaml_file, "w") as f:
            f.write("")

        result = self.yaml_keywords.read_yaml_file_as_string(yaml_file)

        self.assertEqual(result, "")

    def test_read_yaml_file_as_string_multi_document(self):
        """Test reading multi-document YAML file."""
        yaml_content = """---
apiVersion: v1
kind: ConfigMap
metadata:
  name: config1
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: config2
"""
        yaml_file = os.path.join(self.temp_dir, "multi-doc.yaml")
        with open(yaml_file, "w") as f:
            f.write(yaml_content)

        result = self.yaml_keywords.read_yaml_file_as_string(yaml_file)

        # Verify it returns the complete multi-document YAML
        self.assertEqual(result, yaml_content)
        # Verify it's valid (doesn't raise exception)
        self.assertIsInstance(result, str)

    def test_read_yaml_file_as_string_with_special_characters(self):
        """Test reading YAML with special characters and unicode."""
        yaml_content = """apiVersion: v1
kind: ConfigMap
metadata:
  name: special-chars
data:
  message: "Hello 世界! 🚀"
  emoji: "✅ ❌ ⚠️"
  special: "tab:\tand newline:\n"
"""
        yaml_file = os.path.join(self.temp_dir, "special.yaml")
        with open(yaml_file, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        result = self.yaml_keywords.read_yaml_file_as_string(yaml_file)

        self.assertEqual(result, yaml_content)
        # Verify it's valid YAML
        parsed = yaml.safe_load(result)
        self.assertIsNotNone(parsed)

    def test_read_yaml_file_as_string_multi_document_invalid(self):
        """Test reading multi-document YAML with one invalid document."""
        yaml_content = """---
apiVersion: v1
kind: ConfigMap
metadata:
  name: config1
---
invalid: yaml: content:
  bad indentation
"""
        yaml_file = os.path.join(self.temp_dir, "multi-invalid.yaml")
        with open(yaml_file, "w") as f:
            f.write(yaml_content)

        with self.assertRaises(yaml.YAMLError) as context:
            self.yaml_keywords.read_yaml_file_as_string(yaml_file)

        # Verify error message contains file path
        self.assertIn(yaml_file, str(context.exception))


if __name__ == "__main__":
    unittest.main()
