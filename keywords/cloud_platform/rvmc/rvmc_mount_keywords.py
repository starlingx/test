"""Keywords to mount a seed ISO on a subcloud via the platform RVMC.

Mounts the onsite-restore seed ISO on the target subcloud as Redfish virtual media
by invoking the System Controller's own rvmc_install.py. For the "without
reinstall" flow two RVMC operations are excluded:

- set_boot_override: the seed is inserted as virtual media without changing the
  next boot device (no reinstall).
- poweroff_host: the subcloud is left running across the insert, so inserting the
  seed emits a udev "change" event on the CD/DVD device (sr*). The platform rule
  99-seediso.rules only triggers cloud-init-seed.service on a "change" event for
  sr* devices; a seed present at boot (which a power-cycle would produce) emits
  "add" and never triggers the restore.
"""

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.oam.system_oam_show_keywords import SystemOamShowKeywords
from keywords.files.file_keywords import FileKeywords

# Absolute path of the platform RVMC install script on the System Controller.
RVMC_INSTALL_SCRIPT = "/usr/local/bin/rvmc_install.py"
# Platform-generated per-subcloud RVMC config (authoritative BMC address, username
# and base64 password). We reuse it and only override its 'image:' line.
PLATFORM_RVMC_CONFIG_TEMPLATE = "/opt/dc-vault/ansible/{subcloud_name}/rvmc-config.yaml"
# HTTPS port the SC serves staged ISOs on comes from the onsite_restore config.
# Operations excluded for the onsite-restore (without reinstall) flow.
#
# RVMC's operation order (dccommon/rvmc.py) is:
#   eject_image -> poweroff_host -> insert_image -> set_boot_override -> poweron_host
#
# - set_boot_override is excluded so the seed is mounted as virtual media without
#   changing the next boot device to CD/DVD (no reinstall).
# - poweroff_host is excluded so the subcloud is NOT powered off before the insert.
#   The seed is therefore inserted into the already-running subcloud OS, which emits
#   a udev ACTION=="change" event on the CD/DVD device (sr*). The platform udev rule
#   /etc/udev/rules.d/99-seediso.rules only triggers cloud-init-seed.service on a
#   "change" event for sr* devices; a seed present at boot generates "add" (not
#   "change") and never triggers the service. Excluding poweroff_host keeps the box
#   running across the insert so the restore is actually triggered.
EXCLUDED_OPERATION_SET_BOOT_OVERRIDE = "set_boot_override"
EXCLUDED_OPERATION_POWEROFF_HOST = "poweroff_host"
# Excluded operations passed to rvmc_install.py --excluded_operations (comma-separated).
ONSITE_RESTORE_EXCLUDED_OPERATIONS = (
    EXCLUDED_OPERATION_SET_BOOT_OVERRIDE,
    EXCLUDED_OPERATION_POWEROFF_HOST,
)


class RvmcMountKeywords(BaseKeyword):
    """Keywords to mount a subcloud seed ISO via the platform rvmc_install.py."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize RvmcMountKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active System Controller.
        """
        self.ssh_connection = ssh_connection
        self.onsite_restore_config = ConfigurationManager.get_backup_restore_config().get_onsite_restore_config()
        self.file_keywords = FileKeywords(ssh_connection)

    def mount_seed_iso(self, subcloud_name: str, staged_server_path: str, exclude_boot_override: bool = True) -> None:
        """Mount the seed ISO on the subcloud via the platform rvmc_install.py.

        Builds (or reuses) the subcloud RVMC config pointing at the staged seed
        ISO's HTTPS URL, then runs rvmc_install.py. For onsite restore without
        reinstall, set_boot_override and poweroff_host are excluded so the boot
        order is not changed and the seed is inserted into the running subcloud
        (triggering cloud-init-seed via a udev "change" event).

        Args:
            subcloud_name (str): Name of the target subcloud.
            staged_server_path (str): HTTPS-tree server path of the staged seed ISO
                (as returned by SeedIsoStagingKeywords.stage_seed_iso_to_https).
            exclude_boot_override (bool): When True (default), use the "without
                reinstall" exclusions (set_boot_override + poweroff_host).
        """
        image_url = self._to_https_url(staged_server_path)
        rvmc_config_path = self._prepare_rvmc_config(subcloud_name, image_url)
        self._run_rvmc_install(subcloud_name, rvmc_config_path, exclude_boot_override)

    def _to_https_url(self, staged_server_path: str) -> str:
        """Convert a staged seed ISO server path into its SC HTTPS URL.

        The SC serves <www_iso_base_path> at the '/iso' URL root, so a staged path
        '<www_iso_base_path>/<...>/seed.iso' maps to
        'https://[<sc_oam>]:<sc_https_iso_port>/iso/<...>/seed.iso'.

        Args:
            staged_server_path (str): HTTPS-tree server path of the staged seed ISO.

        Returns:
            str: The HTTPS URL to the seed ISO.
        """
        www_base = self.onsite_restore_config.get_www_iso_base_path()
        relative_path = staged_server_path.replace(www_base, "").lstrip("/")

        sc_oam_ip = SystemOamShowKeywords(self.ssh_connection).oam_show().get_oam_floating_ip()
        host = f"[{sc_oam_ip}]" if ":" in sc_oam_ip else sc_oam_ip
        port = self.onsite_restore_config.get_sc_https_iso_port()
        image_url = f"https://{host}:{port}/iso/{relative_path}"
        get_logger().log_info(f"Seed ISO image URL: {image_url}")
        return image_url

    def _prepare_rvmc_config(self, subcloud_name: str, image_url: str) -> str:
        """Prepare the RVMC config file for the subcloud pointing at the seed ISO.

        Reuses the platform-generated RVMC config
        (/opt/dc-vault/ansible/<subcloud>/rvmc-config.yaml) which already contains
        the authoritative BMC address, username and base64-encoded password the
        platform uses. Only the 'image:' line is overridden to point at our staged
        onsite-restore seed ISO. This avoids re-deriving/encoding BMC credentials
        (which can differ per subcloud, e.g. username sysadmin vs Administrator).

        Args:
            subcloud_name (str): Name of the target subcloud.
            image_url (str): HTTPS URL of the staged seed ISO.

        Returns:
            str: Absolute path of the prepared RVMC config file on the SC.

        Raises:
            FileNotFoundError: If the platform RVMC config is not present.
        """
        platform_rvmc_config = PLATFORM_RVMC_CONFIG_TEMPLATE.format(subcloud_name=subcloud_name)
        if not self.file_keywords.validate_file_exists_with_sudo(platform_rvmc_config):
            raise FileNotFoundError(f"Platform RVMC config not found at {platform_rvmc_config}; cannot build RVMC config for {subcloud_name}.")

        rvmc_config_path = f"{self.onsite_restore_config.get_seed_stage_path()}/{subcloud_name}/rvmc-config.yaml"
        get_logger().log_info(f"Preparing RVMC config {rvmc_config_path} from {platform_rvmc_config} (image -> {image_url})")

        # Copy the platform config (authoritative BMC fields) then override image:.
        self.file_keywords.copy_file(platform_rvmc_config, rvmc_config_path, sudo=True)
        self.file_keywords.replace_line_matching(rvmc_config_path, "image:.*", f'image: "{image_url}"')
        # No ACE keyword sets a specific file mode (make_executable is +x only), so a
        # raw send restricts the RVMC config (which contains a BMC secret) to 600.
        self.ssh_connection.send(f"chmod 600 {rvmc_config_path}")

        return rvmc_config_path

    def _run_rvmc_install(self, subcloud_name: str, rvmc_config_path: str, exclude_boot_override: bool) -> None:
        """Run the platform rvmc_install.py to mount the seed ISO.

        Args:
            subcloud_name (str): Name of the target subcloud (RVMC target/tracking name).
            rvmc_config_path (str): Path to the RVMC config file on the SC.
            exclude_boot_override (bool): When True, apply the "without reinstall"
                exclusions (set_boot_override + poweroff_host).
        """
        cmd = f"{RVMC_INSTALL_SCRIPT} " f"--subcloud_name {subcloud_name} " f"--config_file {rvmc_config_path}"
        if exclude_boot_override:
            # Exclude set_boot_override (no reinstall) AND poweroff_host, so the seed is
            # inserted into the running subcloud and cloud-init-seed is triggered via a
            # udev "change" event on sr*. rvmc_install.py takes --excluded_operations as a
            # single string and splits it on commas (type=str; value.split(",")), so the
            # operations are passed as one comma-separated value.
            excluded = ",".join(ONSITE_RESTORE_EXCLUDED_OPERATIONS)
            cmd += f" --excluded_operations {excluded}"

        get_logger().log_info(f"Running RVMC mount: {cmd}")
        self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
