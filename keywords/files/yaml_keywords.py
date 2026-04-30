import os
import textwrap
from typing import Optional

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

    def __init__(self, ssh_connection: Optional[SSHConnection] = None):
        """Constructor.

        Args:
            ssh_connection (Optional[SSHConnection]): The SSH connection
                object. Required for remote operations such as
                generate_yaml_file_from_template with copy_to_remote=True.
                Can be omitted for local-only operations such as
                render_yaml_from_template and load_yaml.
        """
        self.ssh_connection = ssh_connection

    def generate_yaml_file_from_template(self, template_file: str, replacement_dictionary: dict, target_file_name: str, target_remote_location: str, copy_to_remote: bool = True, preserve_order: bool = False) -> str:
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
            preserve_order (bool): When True, writes the rendered Jinja2 output directly without
                re-serializing through yaml.dump, preserving the original key order from the template.
                Defaults to False for backward compatibility.

        Returns:
            str: Path to the generated YAML file, either local or remote depending on `copy_to_remote`.
        """
        # Load the Template YAML file.
        with open(template_file, "r") as template_file:
            yaml_template = template_file.read()

        # Render the YAML file by replacing the tokens.
        template = Template(yaml_template)
        rendered_yaml_string = template.render(replacement_dictionary)
        if preserve_order:
            rendered_yaml = rendered_yaml_string
        else:
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

    def render_yaml_from_template(self, template_file: str, replacement_dictionary: dict) -> str:
        """Render a Jinja2 template and validate the output as valid YAML.

        Performs local rendering only with no SSH, file copy, or logging
        side effects. Use generate_yaml_file_from_template() when remote
        file upload or log folder persistence is needed.

        Args:
            template_file (str): Path to the Jinja2 template file.
            replacement_dictionary (dict): Placeholder keys and their
                replacement values.

        Returns:
            str: Rendered and validated YAML string.

        Raises:
            yaml.YAMLError: If the rendered output is not valid YAML.
            FileNotFoundError: If the template file does not exist.
        """
        with open(template_file, "r") as f:
            rendered = Template(f.read()).render(replacement_dictionary)

        # Validate YAML (supports single or multi-document YAML)
        list(yaml.safe_load_all(rendered))

        return rendered

    def load_yaml(self, file_path: str) -> dict:
        """
        This function will load a yaml file from the local dir.

        Args:
            file_path (str): Path to the YAML file.
                Example: 'resources/cloud_platform/folder/file_name'.

        Returns:
            dict: The loaded YAML file as a Python object.
        """
        with open(file_path, "r") as file:
            return yaml.safe_load(file)

    def format_base64_for_yaml(self, base64_string: str) -> str:
        """Format base64 content for YAML literal block with proper indentation.

        Args:
            base64_string (str): Base64 encoded string

        Returns:
            str: Formatted base64 content for YAML with 76-char lines and 4-space indentation
        """
        clean_base64 = base64_string.replace("\n", "").replace("\r", "").strip()
        lines = textwrap.wrap(clean_base64, width=76, break_long_words=True, break_on_hyphens=False)
        first_line = lines[0]
        remaining = textwrap.indent("\n".join(lines[1:]), "    ")
        formatted = f"{first_line}\n{remaining}" if len(lines) > 1 else first_line
        return formatted

    def read_yaml_file_as_string(self, yaml_file: str, encoding: str = "utf-8") -> str:
        """
        Reads a YAML file and returns its contents as a string.

        Validates YAML syntax before returning to ensure valid content.
        Complements load_yaml() which returns parsed dict.

        Args:
            yaml_file (str): Path to the YAML file.
            encoding (str): File encoding to use when reading. Defaults to 'utf-8'.

        Returns:
            str: Contents of the YAML file as a string.

        Raises:
            yaml.YAMLError: If the YAML file has invalid syntax.
            FileNotFoundError: If the file does not exist.
        """
        with open(yaml_file, "r", encoding=encoding) as f:
            content = f.read()

        # Validate YAML syntax before returning
        # Use safe_load_all to support both single and multi-document YAML
        try:
            list(yaml.safe_load_all(content))
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML syntax in {yaml_file}: {e}")

        return content

    def update_yaml_key_value(self, yaml_file: str, key: str, value: str) -> None:
        """
        Updates a key-value pair in a YAML file.

        Args:
            yaml_file (str): Path to the YAML file.
            key (str): The key to update.
            value (str): The new value for the key.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the YAML file has invalid syntax.
        """
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        data[key] = value
        
        with open(yaml_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
