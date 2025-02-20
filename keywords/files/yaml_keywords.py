import os

import yaml
from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from jinja2 import Environment, FileSystemLoader, Template
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
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def generate_yaml_file_from_template(self, template_file: str, replacement_dictionary: str, target_file_name: str, target_remote_location: str) -> str:
        """
        This function will generate a YAML file from the specified template. The parameters in the file will get substituted by
        using the key-value pairs from the replacement_dictionary. A copy of the file will be stored in the logs folder as 'target_file_name'.
        It will then be SCPed over to 'target_remote_location' on the machine to which this SSH connection is connected.

        Args:
            template_file: Path in the repo to the Template YAML file. e.g. 'resources/cloud_platform/folder/file_name'
            replacement_dictionary: A dictionary containing all the variables to replace in the template and the values that you want.
                                    e.g. { pod_name: 'awesome_pod_name', memory: '2Gb'}
            target_file_name: The name of the 'new' file that will get generated from this function.
            target_remote_location: The folder location on the 'sshed-server' where we want to place the new file.

        Returns: The file name and path of the target_remote_file.

        """

        # Load the Template YAML file.
        with open(template_file, 'r') as template_file:
            yaml_template = template_file.read()

        # Render the YAML file by replacing the tokens.
        template = Template(yaml_template)
        rendered_yaml_string = template.render(replacement_dictionary)
        yaml_data = yaml.safe_load(rendered_yaml_string)
        rendered_yaml = yaml.dump(yaml_data)

        # Create the new file in the log folder.
        log_folder = ConfigurationManager.get_logger_config().get_test_case_resources_log_location()
        rendered_yaml_file_location = os.path.join(log_folder, target_file_name)
        with open(rendered_yaml_file_location, 'w') as f:
            f.write(rendered_yaml)
        get_logger().log_info(f"Generated YAML file from template: {rendered_yaml_file_location}")

        # Upload the file to the remote location
        target_remote_file = f"{target_remote_location}/{target_file_name}"
        FileKeywords(self.ssh_connection).upload_file(rendered_yaml_file_location, target_remote_file)
        return target_remote_file
