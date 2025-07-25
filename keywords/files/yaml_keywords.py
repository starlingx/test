import os

import yaml
from jinja2 import Template

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords


class YamlKeywords(BaseKeyword):
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

    def generate_yaml_file_from_template(self, template_file: str, replacement_dictionary: dict, target_file_name: str, target_remote_location: str, copy_to_remote: bool = True) -> str:
        """
        This function will generate a YAML file from the specified template.

        The parameters in the file will get substituted by using the key-value pairs from the replacement_dictionary. A copy of the file will be stored in the logs folder as 'target_file_name'.
        It will then be SCPed over to 'target_remote_location' on the machine to which this SSH connection is connected.

        Args:
            template_file (str): Path to the template YAML file.
                Example: 'resources/cloud_platform/folder/file_name'.

            replacement_dictionary (dict): Dictionary containing placeholder keys and their replacement values.
                Example: { 'pod_name': 'awesome_pod_name', 'memory': '2Gb' }.

            target_file_name (str): Name of the generated YAML file.
            target_remote_location (str): Remote directory path where the file will be uploaded if `copy_to_remote` is True.
            copy_to_remote (bool): Flag indicating whether to upload the file to a remote location. Defaults to True.

        Returns:
            str: Path to the generated YAML file, either local or remote depending on `copy_to_remote`.
        """
        # Load the Template YAML file.
        with open(template_file, "r") as template_file:
            yaml_template = template_file.read()

        # Render the YAML file by replacing the tokens.
        template = Template(yaml_template)
        rendered_yaml_string = template.render(replacement_dictionary)
        yaml_data_list = list(yaml.safe_load_all(rendered_yaml_string))
        rendered_yaml = "---\n".join([yaml.dump(data, default_flow_style=False) for data in yaml_data_list])

        # Create the new file in the log folder.
        log_folder = ConfigurationManager.get_logger_config().get_test_case_resources_log_location()
        rendered_yaml_file_location = os.path.join(log_folder, target_file_name)
        with open(rendered_yaml_file_location, "w") as f:
            f.write(rendered_yaml)
        get_logger().log_info(f"Generated YAML file from template: {rendered_yaml_file_location}")
        # Upload the file to the remote location
        if copy_to_remote:
            target_remote_file = f"{target_remote_location}/{target_file_name}"
            FileKeywords(self.ssh_connection).upload_file(rendered_yaml_file_location, target_remote_file)
            return target_remote_file
        return rendered_yaml_file_location

    def load_yaml(self, file_path):
        """
        This function will load a yaml file from the local dir

        Args:
            file_path (str): Path to the YAML file.
                Example: 'resources/cloud_platform/folder/file_name'.

        Returns:
            file: The loaded YAML file
        """
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)