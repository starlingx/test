from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Optional

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.exceptions.redfish_client_unreachable_exception import RedFishClientUnreachable
from framework.logging.automation_logger import get_logger
from framework.redfish.objects.bios import Bios
from framework.redfish.objects.system_info import SystemInfo
from framework.redfish.operations.bios_operations import BiosOperations
from framework.redfish.operations.get_system_info import GetSystemInfo
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.bmc.ipmitool.is_ipmitool_keywords import IsIPMIToolKeywords
from keywords.bmc.ipmitool.mc.info.ipmitool_mc_info_keywords import IPMIToolMcInfoKeywords
from keywords.cloud_platform.bios.objects.bios_export_artifact_writer import BiosExportArtifactWriter
from keywords.cloud_platform.bios.objects.bios_export_host_summary_object import BiosExportHostSummaryObject
from keywords.cloud_platform.bios.objects.bios_export_manifest_object import BiosExportManifestObject
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.objects.proc_cmdline_output import ProcCmdlineOutput
from keywords.files.file_keywords import FileKeywords
from keywords.linux.cpu_power.cpu_power_keywords import CpuPowerKeywords
from keywords.linux.dmi.dmi_keywords import DmiKeywords

MAX_PARALLEL_HOSTS = 4
REDFISH_NODE_CAPABILITIES = ("lab_has_bmc_redfish", "lab_has_bmc_dynamic")

# Failures a source is expected to produce when a host or BMC is unreachable or
# misbehaves: keyword and Redfish client errors, failed return-code validation
# (AssertionError), a rejected Redfish request (RuntimeError) and network or
# timeout errors (OSError). Anything else is a bug and propagates.
EXPECTED_SOURCE_ERRORS = (KeywordException, RedFishClientUnreachable, AssertionError, RuntimeError, OSError)


class BiosSettingsExportKeywords(BaseKeyword):
    """Export the BIOS settings of every lab host as JSON artifacts.

    Each host contributes what it can expose. A source that fails with an
    expected connection or command error is recorded in that host's summary and
    the host is reported as partial, so one unreachable BMC does not abort the
    export. Unexpected errors are not caught and fail the caller.

    Sources per host:
        - host/boot_parameters: kernel command line (/proc/cmdline)
        - host/bios_identity: BIOS, system and board identity (DMI)
        - host/cpu_power_settings: effective P-state, C-state, turbo and SMT
        - ipmi/mc_info: BMC identity and firmware (in-band ipmitool)
        - redfish/system: BIOS version and system identity (Redfish)
        - redfish/bios: BIOS attributes (Redfish)

    BaseKeyword logs the arguments of every method, so no method here receives
    BMC credentials or an artifact payload. BMC credentials are read from the
    lab configuration inside the method that needs them and artifacts are
    written through BiosExportArtifactWriter.
    """

    def export_lab_bios_settings(self, output_dir: Optional[str] = None) -> str:
        """Capture the BIOS settings of every configured lab host.

        Hosts are captured in parallel. The layout is
        ``<output_dir>/configuration_manifest.json`` plus one folder per host
        holding ``collection_summary.json`` and one JSON file per source.

        Args:
            output_dir (Optional[str]): Destination folder. Defaults to
                ``lab_configuration`` inside the current session's log folder.

        Returns:
            str: Path to the configuration manifest.

        Raises:
            ValueError: If the lab configuration has no nodes.
        """
        hostnames = [node.get_name() for node in ConfigurationManager.get_lab_config().get_nodes()]
        if not hostnames:
            raise ValueError("Lab configuration must contain nodes to export BIOS settings")
        destination = Path(output_dir) if output_dir else Path(get_logger().get_log_folder()) / "lab_configuration"
        destination.mkdir(parents=True, exist_ok=True)

        manifest = BiosExportManifestObject()
        with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_HOSTS, len(hostnames))) as executor:
            futures = [executor.submit(self.export_host_bios_settings, hostname, destination / hostname) for hostname in hostnames]
            for future in as_completed(futures):
                manifest.add_host_summary(future.result())

        manifest_path = destination / "configuration_manifest.json"
        BiosExportArtifactWriter().write_json(manifest_path, manifest.to_dictionary())
        get_logger().log_info(f"Lab BIOS settings ({manifest.get_status()}) saved to {destination}")
        return str(manifest_path)

    def export_host_bios_settings(self, hostname: str, host_dir: Path) -> BiosExportHostSummaryObject:
        """Capture every available source of one host.

        Args:
            hostname (str): Lab configuration node name.
            host_dir (Path): Folder that receives this host's artifacts.

        Returns:
            BiosExportHostSummaryObject: Collection status of every source of the host.
        """
        host_dir.mkdir(parents=True, exist_ok=True)
        summary = BiosExportHostSummaryObject(hostname)

        ssh_connection = self.collect_source(host_dir, summary, "host", "ssh_connection", lambda: LabConnectionKeywords().get_ssh_for_hostname(hostname), save=False)
        if ssh_connection is not None:
            self.collect_source(host_dir, summary, "host", "boot_parameters", lambda: self.get_boot_parameters(ssh_connection))
            self.collect_source(host_dir, summary, "host", "bios_identity", lambda: DmiKeywords(ssh_connection).get_bios_identity().to_dictionary())
            self.collect_source(host_dir, summary, "host", "cpu_power_settings", lambda: CpuPowerKeywords(ssh_connection).get_cpu_power_settings().to_dictionary())
            self.export_ipmi(host_dir, summary, ssh_connection)
        self.export_redfish(host_dir, summary, hostname)

        BiosExportArtifactWriter().write_json(host_dir / "collection_summary.json", summary.to_dictionary())
        get_logger().log_info(f"BIOS settings of {hostname} ({summary.get_status()}) saved to {host_dir}")
        return summary

    def export_ipmi(self, host_dir: Path, summary: BiosExportHostSummaryObject, ssh_connection: SSHConnection) -> None:
        """Capture BMC information through the host's local IPMI device.

        Args:
            host_dir (Path): Folder that receives this host's artifacts.
            summary (BiosExportHostSummaryObject): Host collection status, updated in place.
            ssh_connection (SSHConnection): Connection to the host.
        """
        if not IsIPMIToolKeywords(ssh_connection).is_ipmi_tool_available():
            summary.add_unsupported_source("ipmi/mc_info", "ipmitool or the local IPMI device is not available on the host")
            return
        self.collect_source(host_dir, summary, "ipmi", "mc_info", lambda: IPMIToolMcInfoKeywords(ssh_connection).get_ipmitool_mc_info().to_dictionary())

    def export_redfish(self, host_dir: Path, summary: BiosExportHostSummaryObject, hostname: str) -> None:
        """Capture the BIOS version and attributes published by the host's BMC over Redfish.

        Only hosts whose scanned node capabilities advertise a Redfish-capable BMC
        are queried, so labs without Redfish do not wait on connection retries.

        Args:
            host_dir (Path): Folder that receives this host's artifacts.
            summary (BiosExportHostSummaryObject): Host collection status, updated in place.
            hostname (str): Lab configuration node name.
        """
        node = ConfigurationManager.get_lab_config().get_node(hostname)
        if not any(capability in (node.get_node_capabilities() or []) for capability in REDFISH_NODE_CAPABILITIES):
            summary.add_unsupported_source("redfish", f"Node capabilities do not include any of {list(REDFISH_NODE_CAPABILITIES)}")
            return
        if not all((node.get_bm_ip(), node.get_bm_username(), self._get_bm_password(hostname))):
            summary.add_unsupported_source("redfish", "BMC address or credentials are not configured")
            return
        self.collect_source(host_dir, summary, "redfish", "system", lambda: self.get_redfish_system(hostname).to_bios_identity_dictionary())
        self.collect_source(host_dir, summary, "redfish", "bios", lambda: self.get_redfish_bios(hostname).to_dictionary())

    def get_boot_parameters(self, ssh_connection: SSHConnection) -> str:
        """Read the running kernel command line.

        Args:
            ssh_connection (SSHConnection): Connection to the host.

        Returns:
            str: Kernel command line.
        """
        lines = FileKeywords(ssh_connection).read_file("/proc/cmdline")
        return ProcCmdlineOutput("\n".join(lines)).get_cmdline()

    def get_redfish_system(self, hostname: str) -> SystemInfo:
        """Read the Redfish computer system of a host's BMC.

        Args:
            hostname (str): Lab configuration node name.

        Returns:
            SystemInfo: System identity and BIOS version.
        """
        node = ConfigurationManager.get_lab_config().get_node(hostname)
        get_system_info = GetSystemInfo(node.get_bm_ip(), node.get_bm_username(), self._get_bm_password(hostname))
        # Resolves the system URI that get_system_info() reads.
        get_system_info.get_system_id()
        return get_system_info.get_system_info()

    def get_redfish_bios(self, hostname: str) -> Bios:
        """Read the BIOS attributes currently in effect on a host's BMC.

        Args:
            hostname (str): Lab configuration node name.

        Returns:
            Bios: BIOS resource with its attribute registry and attributes.
        """
        node = ConfigurationManager.get_lab_config().get_node(hostname)
        return BiosOperations(node.get_bm_ip(), node.get_bm_username(), self._get_bm_password(hostname)).get_bios()

    def collect_source(self, host_dir: Path, summary: BiosExportHostSummaryObject, category: str, name: str, collector: Callable[[], Any], save: bool = True) -> Any:
        """Run one collector, save its result and record its status.

        Only the expected connection and command failures are recorded; any
        other exception propagates so a bug in the capture is not hidden.

        Args:
            host_dir (Path): Folder that receives this host's artifacts.
            summary (BiosExportHostSummaryObject): Host collection status, updated in place.
            category (str): Source category (host, ipmi or redfish).
            name (str): Source name within the category.
            collector (Callable[[], Any]): Keyword call producing the value.
            save (bool): Write the value as ``<category>/<name>.json``. Defaults to True.

        Returns:
            Any: The collected value, or None if the collector failed.
        """
        key = f"{category}/{name}"
        try:
            value = collector()
        except EXPECTED_SOURCE_ERRORS as error:
            get_logger().log_warning(f"BIOS settings source {key} failed: {type(error).__name__}: {error}")
            summary.add_failed_source(key, error)
            return None
        if save:
            (host_dir / category).mkdir(exist_ok=True)
            BiosExportArtifactWriter().write_json(host_dir / category / f"{name}.json", value)
            summary.add_collected_source(key, f"{category}/{name}.json")
        else:
            summary.add_collected_source(key)
        return value

    def _get_bm_password(self, hostname: str) -> str:
        """Get the BMC password of a host, falling back to the lab-wide password.

        Args:
            hostname (str): Lab configuration node name.

        Returns:
            str: BMC password.
        """
        lab_config = ConfigurationManager.get_lab_config()
        return lab_config.get_node(hostname).get_bm_password() or lab_config.get_bm_password()
