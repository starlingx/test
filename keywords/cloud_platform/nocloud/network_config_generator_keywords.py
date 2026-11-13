"""Generate a cloud-init v1 network-config for an on-site seed ISO.

The seed's network-config is applied with ifup to bring the subcloud's OAM
interface up so it can reach the System Controller. It must describe the
DC-managed OAM address (external_oam_floating_address), NOT the factory-install
OAM: reusing the factory network-config leaves the subcloud on the wrong address
and the System Controller cannot reach it.

The network-config is built from the subcloud's own bootstrap-values and
install-values (the same inputs dcmanager uses), so the same keyword produces the
correct config for any subcloud/lab:
    - install-values:  bootstrap_interface (-> vlan_link / physical name),
                       bootstrap_vlan (-> vlan_id, when present)
    - bootstrap-values: external_oam_floating_address (-> address),
                        external_oam_gateway_address (-> gateway),
                        external_oam_subnet (-> prefix)
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.dcmanager.bootstrap_values_keywords import BootstrapValuesKeywords
from keywords.files.file_keywords import FileKeywords


class NetworkConfigGeneratorKeywords(BaseKeyword):
    """Generate a cloud-init v1 network-config from bootstrap/install values."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize NetworkConfigGeneratorKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host holding the
                bootstrap-values/install-values files (the System Controller).
        """
        self.ssh_connection = ssh_connection
        self.file_keywords = FileKeywords(ssh_connection)

    def generate_network_config(self, bootstrap_values_path: str, install_values_path: str) -> str:
        """Build a cloud-init v1 network-config string for the OAM interface.

        Args:
            bootstrap_values_path (str): Path to the subcloud bootstrap-values.yaml
                on the SSH host (supplies the OAM address/gateway/subnet).
            install_values_path (str): Path to the subcloud install-values.yaml on
                the SSH host (supplies the bootstrap interface and optional VLAN).

        Returns:
            str: The network-config file contents (cloud-init v1 format).

        Raises:
            ValueError: If a required field is missing from the source files.
        """
        bootstrap_values_keywords = BootstrapValuesKeywords(self.ssh_connection)
        bootstrap = bootstrap_values_keywords.read_remote_yaml(bootstrap_values_path)
        install = bootstrap_values_keywords.read_remote_yaml(install_values_path)

        oam_floating = bootstrap.get("external_oam_floating_address")
        oam_gateway = bootstrap.get("external_oam_gateway_address")
        oam_subnet = str(bootstrap.get("external_oam_subnet", ""))
        interface = install.get("bootstrap_interface")
        vlan = install.get("bootstrap_vlan")

        if not oam_floating or not oam_gateway or not interface:
            raise ValueError(f"Cannot generate network-config: missing required fields (oam_floating={oam_floating}, gateway={oam_gateway}, interface={interface}).")

        prefix = oam_subnet.split("/")[-1] if "/" in oam_subnet else "64"

        if vlan:
            link = f"- type: vlan\n  name: vlan{vlan}\n  vlan_link: {interface}\n  vlan_id: {vlan}\n"
        else:
            link = f"- type: physical\n  name: {interface}\n"
        network_config = f"version: 1\nconfig:\n{link}  subnets:\n  - type: static\n    address: {oam_floating}/{prefix}\n    gateway: {oam_gateway}\n"

        get_logger().log_info(f"Generated network-config: interface={interface}, vlan={vlan}, oam={oam_floating}/{prefix}, gateway={oam_gateway}")
        return network_config

    def write_network_config(self, bootstrap_values_path: str, install_values_path: str, dest_path: str) -> None:
        """Generate the network-config and write it to a destination file.

        Args:
            bootstrap_values_path (str): Path to the subcloud bootstrap-values.yaml.
            install_values_path (str): Path to the subcloud install-values.yaml.
            dest_path (str): Destination path to write the generated network-config.
        """
        content = self.generate_network_config(bootstrap_values_path, install_values_path)
        get_logger().log_info(f"Writing generated network-config to {dest_path}")
        self.file_keywords.create_file_with_heredoc(dest_path, content, is_sudo=True)
