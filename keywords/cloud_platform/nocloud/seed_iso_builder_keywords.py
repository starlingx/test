"""Keywords to build the onsite-restore (without reinstall) seed ISO.

The seed ISO is assembled on the System Controller from the prebuilt
nocloud-factory-install tree (downloaded from the configured release build server),
with MODE set to 'onsite-restore' and a restore-values.yaml carrying the
local_only selection. It is generated with genisoimage (volume label CIDATA) and
staged on the SC HTTPS-served ISO tree so it can be mounted on the subcloud via
RVMC.
"""

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.system.oam.system_oam_show_keywords import SystemOamShowKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.wget.wget_keywords import WgetKeywords

# Name of the nocloud tree directory inside the downloaded tarball.
NOCLOUD_DIR_NAME = "nocloud-factory-install"
# Seed cloud-init flow selected in the seed user-data.
ONSITE_RESTORE_MODE = "onsite-restore"
# Volume label required by the seed user-data ("mount LABEL=CIDATA /opt/nocloud").
SEED_VOLUME_ID = "CIDATA"
# Output seed ISO filename.
SEED_ISO_NAME = "seed.iso"
# Marker file dropped in the working directory to flag it as automation-created.
AUTOMATION_MARKER_NAME = "AUTOMATION_GENERATED.README"
# System Controller home directory holding each subcloud's deployment config.
# Convention (all labs): /home/sysadmin/subcloud-<N>/ with the dcmanager/lab name
# being 'subcloud<N>' (e.g. 'subcloud1' -> '/home/sysadmin/subcloud-1').
SUBCLOUD_HOME_CONFIG_BASE = "/home/sysadmin"
# Seed network-config filename at the nocloud tree root. run-cloud-init-from-seed.sh
# extracts "/network-config" from the ISO ("isoinfo -x /network-config") and applies
# it with ifup, so it must describe the subcloud's real OAM interface/VLAN/address.
# The nocloud tarball ships a PLACEHOLDER here (physical enp2s1, 10.10.10.2/24 IPv4)
# which fails ifup on real (e.g. IPv6 VLAN) subclouds, so it is replaced with the
# subcloud's own factory_install/network-config.
SEED_NETWORK_CONFIG_NAME = "network-config"
# Per-subcloud factory_install subdirectory on the SC holding the real
# network-config and deployment-config.yml staged at factory-install time.
SUBCLOUD_FACTORY_INSTALL_SUBDIR = "factory_install"
# Seed config/ files that the onsite-restore scripts consume (10-platform-reconfig,
# 90-send-onsite-restore-request). The nocloud tarball ships placeholders for these;
# they are overwritten with the subcloud's real files so the scripts don't sys.exit.
SEED_INSTALL_VALUES_NAME = "install-values.yaml"
SEED_DEPLOYMENT_CONFIG_NAME = "deployment-config.yml"


class SeedIsoBuilderKeywords(BaseKeyword):
    """Keywords to build and stage the onsite-restore seed ISO on the SC."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize SeedIsoBuilderKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active System Controller.
        """
        self.ssh_connection = ssh_connection
        self.onsite_restore_config = ConfigurationManager.get_backup_restore_config().get_onsite_restore_config()
        self.file_keywords = FileKeywords(ssh_connection)

    def build_onsite_restore_seed(self, subcloud_name: str, local_only: bool, restore_timeout: int = None) -> str:
        """Build the onsite-restore seed ISO on the SC and stage it on HTTPS.

        Downloads the release-matched nocloud tree, sets MODE=onsite-restore, writes
        the restore-values.yaml (local_only/restore_timeout), and generates the seed
        ISO with genisoimage (volid CIDATA) into the automation working directory.
        Staging the ISO onto the SC HTTPS tree is a separate step
        (SeedIsoStagingKeywords.stage_seed_iso_to_https).

        Args:
            subcloud_name (str): Name of the target subcloud.
            local_only (bool): True to restore from the subcloud's local backup;
                False to have the System Controller transfer the central backup.
            restore_timeout (int): Restore monitoring timeout in seconds. When None,
                the configured default is used.

        Returns:
            str: Path of the built seed ISO in the working directory
                (<seed_stage_path>/<subcloud_name>/seed.iso).
        """
        if restore_timeout is None:
            restore_timeout = self.onsite_restore_config.get_default_restore_timeout()

        software_version = self._get_subcloud_software_version(subcloud_name)
        work_dir = self._get_work_dir(subcloud_name)
        nocloud_dir = f"{work_dir}/{NOCLOUD_DIR_NAME}"

        get_logger().log_info(f"Building onsite-restore seed for '{subcloud_name}' (version {software_version}, local_only={local_only})")

        self._prepare_work_dir(work_dir)
        self._write_automation_marker(work_dir, subcloud_name, software_version)
        self._download_nocloud_tree(software_version, work_dir)
        self._set_mode_onsite_restore(nocloud_dir)
        self._write_restore_values(nocloud_dir, local_only, restore_timeout)
        self._stage_subcloud_config(nocloud_dir, subcloud_name)
        self._stage_network_config(nocloud_dir, subcloud_name)

        seed_iso_path = f"{work_dir}/{SEED_ISO_NAME}"
        self._generate_seed_iso(nocloud_dir, seed_iso_path)

        get_logger().log_info(f"Onsite-restore seed built at {seed_iso_path}")
        return seed_iso_path

    def cleanup(self, subcloud_name: str) -> None:
        """Remove the automation-created seed working directory.

        Removes '<seed_stage_path>/<subcloud_name>/', which contains the downloaded
        nocloud tree, the assembled config, and the built seed ISO. The HTTPS-staged
        copy is removed separately by SeedIsoStagingKeywords.unstage_seed_iso.

        Args:
            subcloud_name (str): Name of the target subcloud.
        """
        work_dir = self._get_work_dir(subcloud_name)
        get_logger().log_info(f"Cleaning up onsite-restore seed working dir: {work_dir}")
        self.file_keywords.delete_folder_with_sudo(work_dir)

    def _get_subcloud_software_version(self, subcloud_name: str) -> str:
        """Return the software version reported by dcmanager for the subcloud.

        Args:
            subcloud_name (str): Name of the target subcloud.

        Returns:
            str: The subcloud software version (e.g. '26.10').
        """
        return DcManagerSubcloudShowKeywords(self.ssh_connection).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    def _get_work_dir(self, subcloud_name: str) -> str:
        """Return the per-subcloud seed working directory on the SC.

        Args:
            subcloud_name (str): Name of the target subcloud.

        Returns:
            str: Absolute working directory path (<seed_stage_path>/<subcloud_name>).
        """
        return f"{self.onsite_restore_config.get_seed_stage_path()}/{subcloud_name}"

    def _prepare_work_dir(self, work_dir: str) -> None:
        """Create a clean working directory on the SC.

        Args:
            work_dir (str): Absolute working directory path.
        """
        if self.file_keywords.file_exists(work_dir):
            self.file_keywords.delete_folder_with_sudo(work_dir)
        self.file_keywords.create_directory(work_dir)

    def _write_automation_marker(self, work_dir: str, subcloud_name: str, software_version: str) -> None:
        """Drop a marker file identifying the working directory as automation-created.

        Args:
            work_dir (str): Absolute working directory path.
            subcloud_name (str): Name of the target subcloud.
            software_version (str): Subcloud software version.
        """
        content = "This directory was created by ACE automation to build the\n" "onsite-restore-without-reinstall seed ISO. It is safe to delete.\n" f"subcloud: {subcloud_name}\n" f"software_version: {software_version}\n" f"keyword: SeedIsoBuilderKeywords\n"
        self.file_keywords.create_file_with_heredoc(f"{work_dir}/{AUTOMATION_MARKER_NAME}", content)

    def _download_nocloud_tree(self, software_version: str, work_dir: str) -> None:
        """Download and extract the release-matched nocloud tree into the work dir.

        Args:
            software_version (str): Subcloud software version used to resolve the URL.
            work_dir (str): Absolute working directory path.
        """
        url = self.onsite_restore_config.resolve_nocloud_tarball_url(software_version)
        tarball_name = self.onsite_restore_config.get_nocloud_tarball_name()
        tarball_path = f"{work_dir}/{tarball_name}"

        WgetKeywords(self.ssh_connection).download_file(url, tarball_path)

        get_logger().log_info(f"Extracting {tarball_path} into {work_dir}")
        # No ACE keyword exists for tar extraction, so a raw send is used here.
        self.ssh_connection.send(f"tar -xf {tarball_path} -C {work_dir}")
        self.validate_success_return_code(self.ssh_connection)

        nocloud_dir = f"{work_dir}/{NOCLOUD_DIR_NAME}"
        if not self.file_keywords.file_exists(nocloud_dir):
            raise FileNotFoundError(f"Expected nocloud tree not found after extraction: {nocloud_dir}")

    def _set_mode_onsite_restore(self, nocloud_dir: str) -> None:
        """Set the seed user-data MODE to 'onsite-restore'.

        Args:
            nocloud_dir (str): Path to the extracted nocloud tree.
        """
        user_data_path = f"{nocloud_dir}/user-data"
        get_logger().log_info(f"Setting MODE={ONSITE_RESTORE_MODE} in {user_data_path}")
        # Replace the 'MODE=<something>' assignment line, preserving indentation.
        self.file_keywords.replace_line_matching(user_data_path, "MODE=.*", f"MODE={ONSITE_RESTORE_MODE}")

    def _write_restore_values(self, nocloud_dir: str, local_only: bool, restore_timeout: int) -> None:
        """Write the seed restore-values.yaml (local_only and restore_timeout).

        Args:
            nocloud_dir (str): Path to the extracted nocloud tree.
            local_only (bool): local_only selection for the onsite restore.
            restore_timeout (int): Restore monitoring timeout in seconds.
        """
        restore_values_path = f"{nocloud_dir}/config/restore-values.yaml"
        content = f"local_only: {str(local_only).lower()}\n" f"restore_timeout: {restore_timeout}\n"
        get_logger().log_info(f"Writing {restore_values_path} (local_only={local_only}, restore_timeout={restore_timeout})")
        self.file_keywords.create_file_with_heredoc(restore_values_path, content)

    def _get_subcloud_home_config_dir(self, subcloud_name: str) -> str:
        """Return the SC home config directory for a subcloud.

        All labs store each subcloud's deployment config at
        /home/sysadmin/subcloud-<N>/, while the dcmanager/lab name is
        'subcloud<N>' (e.g. 'subcloud1' -> '/home/sysadmin/subcloud-1'). The derived
        path is validated to exist so a naming mismatch fails here with a clear
        message instead of surfacing later as an unrelated FileNotFoundError.

        Args:
            subcloud_name (str): The dcmanager/lab subcloud name (e.g. 'subcloud1').

        Returns:
            str: Absolute path '/home/sysadmin/subcloud-<N>'.

        Raises:
            FileNotFoundError: If the derived home config directory does not exist
                on the System Controller.
        """
        folder_name = subcloud_name.replace("subcloud", "subcloud-", 1) if subcloud_name.startswith("subcloud") and not subcloud_name.startswith("subcloud-") else subcloud_name
        home_config_dir = f"{SUBCLOUD_HOME_CONFIG_BASE}/{folder_name}"
        if not self.file_keywords.validate_file_exists_with_sudo(home_config_dir):
            raise FileNotFoundError(f"Subcloud home config directory not found at {home_config_dir} for subcloud '{subcloud_name}'; " f"expected the subcloud's deployment config staged under {SUBCLOUD_HOME_CONFIG_BASE}/subcloud-<N>.")
        return home_config_dir

    def _get_subcloud_factory_password(self, subcloud_name: str) -> str:
        """Return the subcloud's factory sysadmin password from lab config.

        The seed runs while the subcloud is at factory-restore baseline, so the
        sysadmin password injected into the seed bootstrap-values is the subcloud's
        factory password. Uses the subcloud's factory_credentials, falling back to
        admin_credentials when factory_credentials are not configured (mirroring
        LabConnectionKeywords.get_subcloud_factory_ssh).

        Args:
            subcloud_name (str): The dcmanager/lab subcloud name.

        Returns:
            str: The subcloud factory sysadmin password.
        """
        subcloud_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
        factory_credentials = subcloud_config.get_factory_credentials()
        credentials = factory_credentials if factory_credentials else subcloud_config.get_admin_credentials()
        return credentials.get_password()

    def _stage_subcloud_config(self, nocloud_dir: str, subcloud_name: str) -> None:
        """Stage the subcloud config files into the seed config dir.

        The nocloud tarball ships TEMPLATE/placeholder files under config/. The seed
        onsite-restore scripts (10-platform-reconfig, 90-send-onsite-restore-request)
        require the subcloud's REAL config, so this method overwrites them from the
        subcloud's SC-side deployment config (/home/sysadmin/subcloud-<N>/, present on
        every lab) to match a known-good hand-built onsite-restore seed:

        - config/bootstrap-values.yaml: the real subcloud bootstrap-values, with
          systemcontroller_oam_address and sysadmin_password injected (neither is in
          the per-subcloud file but both are required by the seed scripts), and
          ssl_ca_cert rewritten to the bare cert filename shipped alongside it.
        - config/<cert>: the SSL CA cert, so install_ssl_ca() can resolve ssl_ca_cert
          relative to config/.
        - config/install-values.yaml: required by 10-platform-reconfig.
        - config/deployment-config.yml: copied with the config dir into enroll-config
          at runtime and consumed by 95-trigger-onsite-local-restore.

        Args:
            nocloud_dir (str): Path to the extracted nocloud tree.
            subcloud_name (str): Name of the target subcloud.
        """
        config_dir = f"{nocloud_dir}/config"
        home_config_dir = self._get_subcloud_home_config_dir(subcloud_name)
        factory_install_dir = f"{home_config_dir}/{SUBCLOUD_FACTORY_INSTALL_SUBDIR}"
        get_logger().log_info(f"Staging subcloud config from {home_config_dir} into {config_dir}")
        self.file_keywords.create_directory_with_sudo(config_dir)

        source_bootstrap = self._find_subcloud_bootstrap_values(home_config_dir)
        seed_bootstrap = f"{config_dir}/bootstrap-values.yaml"
        # Overwrite the template bootstrap-values.yaml so exactly one bootstrap-values
        # file (with real values) exists for the seed's find_file glob.
        self.file_keywords.copy_file(source_bootstrap, seed_bootstrap, sudo=True)

        # Inject the System Controller OAM address required by the seed restore
        # script (not present in the subcloud bootstrap-values). Remove any existing
        # entry first, then append the real SC OAM floating IP. A leading newline is
        # included so the entry starts on its own line even if the source file does
        # not end with a trailing newline (otherwise the YAML would be malformed).
        sc_oam_ip = SystemOamShowKeywords(self.ssh_connection).oam_show().get_oam_floating_ip()
        get_logger().log_info(f"Injecting systemcontroller_oam_address={sc_oam_ip} into {seed_bootstrap}")
        self.file_keywords.remove_line_matching(seed_bootstrap, "systemcontroller_oam_address")
        self.file_keywords.append_to_file(seed_bootstrap, f"\nsystemcontroller_oam_address: {sc_oam_ip}")

        # Inject sysadmin_password (not in the per-subcloud bootstrap-values but
        # required by 10-platform-reconfig and 90-send-onsite-restore-request). The
        # subcloud is at factory-restore baseline when the seed runs, so this is the
        # subcloud's factory sysadmin password, taken from lab config.
        sysadmin_password = self._get_subcloud_factory_password(subcloud_name)
        get_logger().log_info(f"Injecting sysadmin_password into {seed_bootstrap}")
        self.file_keywords.remove_line_matching(seed_bootstrap, "sysadmin_password")
        self.file_keywords.append_to_file(seed_bootstrap, f"\nsysadmin_password: {sysadmin_password}")

        self._stage_ssl_ca_cert(config_dir, seed_bootstrap)
        source_install_values = self._find_subcloud_install_values(home_config_dir)
        self._stage_config_file(source_install_values, f"{config_dir}/{SEED_INSTALL_VALUES_NAME}", required=True)
        self._stage_config_file(f"{factory_install_dir}/{SEED_DEPLOYMENT_CONFIG_NAME}", f"{config_dir}/{SEED_DEPLOYMENT_CONFIG_NAME}", required=False)

    def _stage_ssl_ca_cert(self, config_dir: str, seed_bootstrap: str) -> None:
        """Stage the configured SSL CA cert into config/ and set ssl_ca_cert to it.

        The onsite-restore scripts (SubcloudSetup.install_ssl_ca) read ssl_ca_cert
        from bootstrap-values and resolve it relative to config/; they skip the CA
        install when ssl_ca_cert is absent, and fail if it is set but the file is
        missing. The cert filename is environment-specific and is taken from the
        onsite_restore config (ssl_ca_cert_name):

        - When configured, the named cert is copied from the SC home directory into
          config/ and ssl_ca_cert is set to the bare filename so it resolves there.
        - When empty, no cert is staged and any ssl_ca_cert key is removed, so the
          restore proceeds without a CA install.

        Args:
            config_dir (str): The seed config/ directory.
            seed_bootstrap (str): Path to the seed bootstrap-values.yaml.

        Raises:
            FileNotFoundError: If a cert name is configured but the file is missing
                on the SC home directory.
        """
        cert_name = self.onsite_restore_config.get_ssl_ca_cert_name()
        if not cert_name:
            get_logger().log_info("No ssl_ca_cert_name configured; removing ssl_ca_cert from seed bootstrap-values (CA install skipped)")
            self.file_keywords.remove_line_matching(seed_bootstrap, "ssl_ca_cert")
            return

        source_cert = f"{SUBCLOUD_HOME_CONFIG_BASE}/{cert_name}"
        if not self.file_keywords.validate_file_exists_with_sudo(source_cert):
            raise FileNotFoundError(f"Configured SSL CA cert '{cert_name}' not found at {source_cert}; required to build the onsite-restore seed config.")
        seed_cert = f"{config_dir}/{cert_name}"
        get_logger().log_info(f"Staging SSL CA cert {source_cert} -> {seed_cert} and setting ssl_ca_cert")
        self.file_keywords.copy_file(source_cert, seed_cert, sudo=True)
        # Set ssl_ca_cert to the bare filename so it resolves relative to config/.
        self.file_keywords.replace_line_matching(seed_bootstrap, "ssl_ca_cert:.*", f"ssl_ca_cert: {cert_name}")

    def _stage_config_file(self, source_path: str, dest_path: str, required: bool) -> None:
        """Copy a subcloud config file into the seed config dir.

        Args:
            source_path (str): Absolute path of the source file on the SC.
            dest_path (str): Absolute destination path in the seed config dir.
            required (bool): When True, raise if the source file is missing; when
                False, log and skip (the file is optional for the restore flow).

        Raises:
            FileNotFoundError: If required is True and source_path does not exist.
        """
        if not self.file_keywords.validate_file_exists_with_sudo(source_path):
            if required:
                raise FileNotFoundError(f"Required seed config file not found: {source_path}")
            get_logger().log_info(f"Optional seed config file not found, skipping: {source_path}")
            return
        get_logger().log_info(f"Staging seed config file {source_path} -> {dest_path}")
        self.file_keywords.copy_file(source_path, dest_path, sudo=True)

    def _stage_network_config(self, nocloud_dir: str, subcloud_name: str) -> None:
        """Stage the subcloud's real network-config at the seed tree root.

        run-cloud-init-from-seed.sh extracts "/network-config" from the seed ISO and
        applies it with ifup to bring the subcloud's OAM interface up so it can reach
        the System Controller. The nocloud tarball ships a PLACEHOLDER network-config
        (type physical, name enp2s1, static 10.10.10.2/24 IPv4) which fails ifup on a
        real subcloud whose OAM is on a different interface/VLAN and/or is IPv6
        (onsite restore without reinstall).

        The subcloud's own correct network-config is already staged on the SC at
        /home/sysadmin/subcloud-<N>/factory_install/network-config (the VLAN/interface
        /IPv6 address the platform used at factory install, matching the known-good
        hand-built onsite-restore seed), so it is copied verbatim to the seed root.

        Args:
            nocloud_dir (str): Path to the extracted nocloud tree.
            subcloud_name (str): Name of the target subcloud.
        """
        home_config_dir = self._get_subcloud_home_config_dir(subcloud_name)
        source_network_config = f"{home_config_dir}/{SUBCLOUD_FACTORY_INSTALL_SUBDIR}/{SEED_NETWORK_CONFIG_NAME}"
        if not self.file_keywords.validate_file_exists_with_sudo(source_network_config):
            raise FileNotFoundError(f"Subcloud network-config not found at {source_network_config}; required to build the onsite-restore seed.")
        seed_network_config = f"{nocloud_dir}/{SEED_NETWORK_CONFIG_NAME}"
        get_logger().log_info(f"Staging seed network-config {source_network_config} -> {seed_network_config}")
        self.file_keywords.copy_file(source_network_config, seed_network_config, sudo=True)

    def _find_subcloud_bootstrap_values(self, home_config_dir: str) -> str:
        """Return the absolute path of the subcloud bootstrap-values file.

        Args:
            home_config_dir (str): The subcloud home config dir
                (/home/sysadmin/subcloud-<N>).

        Returns:
            str: Absolute path to the subcloud's *bootstrap-values*.yaml file.

        Raises:
            FileNotFoundError: If no bootstrap-values file is found.
        """
        for name in self.file_keywords.get_files_in_dir(home_config_dir):
            if "bootstrap-values" in name and (name.endswith(".yaml") or name.endswith(".yml")):
                return f"{home_config_dir}/{name}"
        raise FileNotFoundError(f"No bootstrap-values file found in {home_config_dir}")

    def _find_subcloud_install_values(self, home_config_dir: str) -> str:
        """Return the absolute path of the subcloud install-values file.

        The file is named with the subcloud prefix on the SC (e.g.
        'subcloud11-install-values.yaml'), so it is matched by substring rather than
        a fixed filename.

        Args:
            home_config_dir (str): The subcloud home config dir
                (/home/sysadmin/subcloud-<N>).

        Returns:
            str: Absolute path to the subcloud's *install-values*.yaml file.

        Raises:
            FileNotFoundError: If no install-values file is found.
        """
        for name in self.file_keywords.get_files_in_dir(home_config_dir):
            if "install-values" in name and (name.endswith(".yaml") or name.endswith(".yml")):
                return f"{home_config_dir}/{name}"
        raise FileNotFoundError(f"No install-values file found in {home_config_dir}")

    def _generate_seed_iso(self, nocloud_dir: str, seed_iso_path: str) -> None:
        """Generate the seed ISO with genisoimage (volume label CIDATA).

        The ISO is written into the automation working directory (which already
        exists); staging to the SC HTTPS tree is a separate step.

        Args:
            nocloud_dir (str): Path to the assembled nocloud tree.
            seed_iso_path (str): Absolute output path for the seed ISO
                (inside the working directory).
        """
        if self.file_keywords.file_exists(seed_iso_path):
            self.file_keywords.delete_file(seed_iso_path)

        cmd = f"genisoimage -o {seed_iso_path} " f"-volid '{SEED_VOLUME_ID}' " f"-untranslated-filenames " f"-joliet " f"-rock " f"-iso-level 2 " f"{nocloud_dir}"
        get_logger().log_info(f"Generating seed ISO: {cmd}")
        # No ACE keyword exists for genisoimage, so a raw send is used here (the
        # auto-installer has an equivalent ISOKeywordsClass.generate_seed_iso).
        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)

        if not self.file_keywords.file_exists(seed_iso_path):
            raise FileNotFoundError(f"Seed ISO was not created: {seed_iso_path}")
