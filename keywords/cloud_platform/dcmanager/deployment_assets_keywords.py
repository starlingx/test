import os

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.cloud_platform.dcmanager.objects.deployment_assets_network_output import DeploymentAssetsNetworkOutput


class DeploymentAssestsKeywords(BaseKeyword):
    """
    This class is responsible for handling of Yaml files.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection object.
        """
        self.ssh_connection = ssh_connection

    def _read_remote_file_lines(self, yaml_file_path: str) -> list[str]:
        """
        Downloads a remote file and returns its lines.

        Args:
            yaml_file_path (str): Path to the remote YAML file.

        Returns:
            list[str]: Lines of the file.
        """
        file_keywords = FileKeywords(self.ssh_connection)
        local_temp_file = f"/tmp/{os.path.basename(yaml_file_path)}"
        file_keywords.download_file(yaml_file_path, local_temp_file)

        with open(local_temp_file, 'r') as file:
            lines = file.readlines()
        os.remove(local_temp_file)

        return lines

    def modify_yaml_to_admin_network_config(self, yaml_file_path: str) -> None:
        """
        Modify YAML file by commenting out management_gateway_address lines
        and uncommenting admin_ lines.

        Args:
            yaml_file_path (str): Path to the YAML file to modify.
        """
        file_keywords = FileKeywords(self.ssh_connection)
        local_temp_file = f"/tmp/{os.path.basename(yaml_file_path)}"

        file_keywords.download_file(yaml_file_path, local_temp_file)

        with open(local_temp_file, 'r') as file:
            lines = file.readlines()

        has_commented_mgmt = any('#management_gateway_address' in line for line in lines)
        has_uncommented_admin = any(line.strip().startswith('admin_') for line in lines)

        if has_commented_mgmt and has_uncommented_admin:
            os.remove(local_temp_file)
            return

        modified_lines = []
        for line in lines:
            if 'management_gateway_address' in line and not line.strip().startswith('#'):
                modified_lines.append('#' + line)
            elif line.strip().startswith('#') and 'admin_' in line:
                modified_lines.append(line.lstrip('#').lstrip())
            else:
                modified_lines.append(line)

        with open(local_temp_file, 'w') as file:
            file.writelines(modified_lines)

        file_keywords.upload_file(local_temp_file, yaml_file_path)
        os.remove(local_temp_file)

    def get_admin_addresses_from_yaml(self, yaml_file_path: str) -> DeploymentAssetsNetworkOutput:
        """
        Extract admin network configuration from remote YAML file.

        Args:
            yaml_file_path (str): Path to the remote YAML file.

        Returns:
            DeploymentAssetsNetworkOutput: Parsed admin network configuration output object.
        """
        lines = self._read_remote_file_lines(yaml_file_path)
        return DeploymentAssetsNetworkOutput(lines, key_prefix='admin')

    def get_values_by_key_prefix(self, yaml_file_path: str, key_prefix: str, filter_type: str = None) -> DeploymentAssetsNetworkOutput:
        """
        Extract all values from keys that match the given prefix from remote YAML file.

        Args:
            yaml_file_path (str): Path to the remote YAML file.
            key_prefix (str): Key prefix to match (e.g., 'management', 'admin').
            filter_type (str): Filter type to validate required suffixes (e.g., 'network').

        Returns:
            DeploymentAssetsNetworkOutput: Parsed network configuration output object.

        Raises:
            KeywordException: If filter_type is 'network' and required suffixes are missing.
        """
        try:
            lines = self._read_remote_file_lines(yaml_file_path)
            return DeploymentAssetsNetworkOutput(lines, key_prefix=key_prefix)
        except Exception as e:
            raise KeywordException(f"Failed to collect values from YAML: {e}") from e
