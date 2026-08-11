"""Keywords for reading and manipulating subcloud bootstrap values on a system controller."""

from typing import List

import yaml

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords


class BootstrapValuesKeywords(BaseKeyword):
    """Keywords for reading and modifying subcloud bootstrap values YAML files.

    Provides methods to read bootstrap/install values from the system controller,
    extract specific sections, and inject configuration from the central cloud.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the system controller.
        """
        self.ssh_connection = ssh_connection

    def read_remote_yaml(self, file_path: str) -> dict:
        """Read a YAML file from the remote host and parse it.

        Args:
            file_path (str): Path to the YAML file on the remote host.

        Returns:
            dict: Parsed YAML content as a dictionary.

        Raises:
            ValueError: If the file content cannot be parsed as valid YAML.
        """
        output = FileKeywords(self.ssh_connection).read_file(file_path)
        content = "\n".join(output)

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML from '{file_path}': {e}")

        if data is None:
            return {}
        return data

    def get_external_registry_from_bootstrap(self, subcloud_name: str) -> str:
        """Check if the subcloud's bootstrap values use an external registry.

        Reads the bootstrap values YAML from the system controller and checks
        docker_registries for any url that does not point to registry.central.

        Args:
            subcloud_name (str): Subcloud name.

        Returns:
            str: External registry hostname or empty string if none found.
        """
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        bootstrap_file = sc_assets.get_bootstrap_file()

        data = self.read_remote_yaml(bootstrap_file)
        docker_registries = data.get("docker_registries", {})

        if not isinstance(docker_registries, dict):
            return ""

        for registry_key, registry_config in docker_registries.items():
            if not isinstance(registry_config, dict):
                continue
            url_value = registry_config.get("url", "")
            if not url_value:
                continue
            # Strip protocol if present
            if "://" in url_value:
                url_value = url_value.split("://", 1)[1]
            # Extract hostname (remove port and path)
            host_port = url_value.split("/")[0]
            hostname = host_port.split(":")[0]
            if hostname and hostname != "registry.central":
                return hostname

        return ""

    def get_oam_interface_from_install_values(self, subcloud_name: str) -> str:
        """Resolve the OAM interface name for a subcloud from its install values.

        If bootstrap_vlan is set, returns the VLAN interface. Otherwise returns
        the bootstrap_interface directly.

        Args:
            subcloud_name (str): Subcloud name.

        Returns:
            str: OAM interface name (physical or VLAN).

        Raises:
            ValueError: If bootstrap_interface is not found in install values.
        """
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        install_file = sc_assets.get_install_file()

        data = self.read_remote_yaml(install_file)

        bootstrap_interface = data.get("bootstrap_interface", "")
        if not bootstrap_interface:
            raise ValueError(f"'bootstrap_interface' not found in install values for subcloud '{subcloud_name}'")

        bootstrap_vlan = data.get("bootstrap_vlan")
        if bootstrap_vlan:
            return f"vlan{bootstrap_vlan}"
        return bootstrap_interface

    def inject_central_registry_into_bootstrap(self, subcloud_name: str, central_bootstrap_file: str, registry_fields: List[str]) -> str:
        """Inject the system controller's registry config into the subcloud's bootstrap values.

        Reads specified fields from the central cloud's bootstrap YAML and injects
        them into the subcloud's bootstrap values file, replacing existing values
        for those fields. Creates a backup first.

        Args:
            subcloud_name (str): Subcloud name.
            central_bootstrap_file (str): Path to the central cloud bootstrap file.
            registry_fields (List[str]): YAML top-level keys to copy from central to subcloud.

        Returns:
            str: Path to the backup file (for teardown restoration).
        """
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        subcloud_bootstrap_file = sc_assets.get_bootstrap_file()
        backup_file = f"{subcloud_bootstrap_file}.bkup"

        file_kw = FileKeywords(self.ssh_connection)

        # Backup original
        file_kw.copy_file(subcloud_bootstrap_file, backup_file)
        get_logger().log_info(f"Backed up subcloud bootstrap values to '{backup_file}'")

        # Read central cloud registry config
        central_data = self.read_remote_yaml(central_bootstrap_file)
        central_sections = {key: central_data[key] for key in registry_fields if key in central_data}
        get_logger().log_info(f"Extracted {len(central_sections)} registry sections from central bootstrap")

        # Read subcloud bootstrap
        subcloud_data = self.read_remote_yaml(subcloud_bootstrap_file)

        # Replace registry sections with central's values
        for field_name in registry_fields:
            if field_name in central_sections:
                subcloud_data[field_name] = central_sections[field_name]
            elif field_name in subcloud_data:
                # Remove field if it's not in central but exists in subcloud
                del subcloud_data[field_name]

        # Write back using yaml.dump to produce valid YAML
        content = yaml.dump(subcloud_data, default_flow_style=False, allow_unicode=True)
        file_kw.create_file_with_heredoc(subcloud_bootstrap_file, content, delimiter="BOOTSTRAP_EOF")
        get_logger().log_info(f"Injected central registry config into '{subcloud_bootstrap_file}'")

        return backup_file

    def restore_bootstrap_from_backup(self, backup_file: str, original_file: str) -> None:
        """Restore the subcloud's bootstrap values from backup.

        Args:
            backup_file (str): Path to the backup file.
            original_file (str): Path to the original bootstrap file to restore.
        """
        FileKeywords(self.ssh_connection).rename_file(backup_file, original_file)
        get_logger().log_info(f"Restored subcloud bootstrap values from '{backup_file}'")
