"""Unit tests for DcManagerSubcloudDeployShowOutput parser."""

import unittest

from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_deploy_show_output import DcManagerSubcloudDeployShowOutput


class TestDcManagerSubcloudDeployShowOutput(unittest.TestCase):
    """Test cases for DcManagerSubcloudDeployShowOutput parser."""

    def setUp(self):
        """Set up test data with real command output."""
        self.sample_output = [
            "+------------------+-------+",
            "| Field            | Value |",
            "+------------------+-------+",
            "| deploy_playbook  | None  |",
            "| deploy_overrides | None  |",
            "| deploy_chart     | None  |",
            "| prestage_images  | None  |",
            "| software_version | 25.09 |",
            "+------------------+-------+"
        ]

    def test_parse_deploy_show_output(self):
        """Test parsing of deploy show output."""
        output = DcManagerSubcloudDeployShowOutput(self.sample_output)
        deploy_obj = output.get_dcmanager_subcloud_deploy_show_object()

        self.assertEqual(deploy_obj.get_deploy_playbook(), "None")
        self.assertEqual(deploy_obj.get_deploy_overrides(), "None")
        self.assertEqual(deploy_obj.get_deploy_chart(), "None")
        self.assertEqual(deploy_obj.get_prestage_images(), "None")
        self.assertEqual(deploy_obj.get_software_version(), "25.09")

    def test_parse_deploy_show_with_values(self):
        """Test parsing of deploy show output with actual values."""
        sample_output_with_values = [
            "+------------------+------------------------+",
            "| Field            | Value                  |",
            "+------------------+------------------------+",
            "| deploy_playbook  | /opt/platform/playbook |",
            "| deploy_overrides | /opt/platform/override |",
            "| deploy_chart     | /opt/platform/chart    |",
            "| prestage_images  | /opt/platform/images   |",
            "| software_version | 25.09                  |",
            "+------------------+------------------------+"
        ]

        output = DcManagerSubcloudDeployShowOutput(sample_output_with_values)
        deploy_obj = output.get_dcmanager_subcloud_deploy_show_object()

        self.assertEqual(deploy_obj.get_deploy_playbook(), "/opt/platform/playbook")
        self.assertEqual(deploy_obj.get_deploy_overrides(), "/opt/platform/override")
        self.assertEqual(deploy_obj.get_deploy_chart(), "/opt/platform/chart")
        self.assertEqual(deploy_obj.get_prestage_images(), "/opt/platform/images")
        self.assertEqual(deploy_obj.get_software_version(), "25.09")

    def test_empty_output(self):
        """Test parsing empty output."""
        empty_output = [
            "+------------------+-------+",
            "| Field            | Value |",
            "+------------------+-------+",
            "+------------------+-------+"
        ]
        output = DcManagerSubcloudDeployShowOutput(empty_output)
        deploy_obj = output.get_dcmanager_subcloud_deploy_show_object()

        self.assertIsNone(deploy_obj.get_deploy_playbook())
        self.assertIsNone(deploy_obj.get_deploy_overrides())
        self.assertIsNone(deploy_obj.get_deploy_chart())
        self.assertIsNone(deploy_obj.get_prestage_images())
        self.assertIsNone(deploy_obj.get_software_version())


if __name__ == '__main__':
    unittest.main()