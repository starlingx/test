"""Exporter baseline preparation and fresh per-node compatibility scrapes."""

import re
from pathlib import PurePosixPath
from shlex import quote

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords import APPLICATION_NAME, NodeInterfaceMetricsExporterKeywords
from keywords.cloud_platform.applications.object.interface_metrics_output import InterfaceMetricsOutput
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.upgrade.object.baseline_application_package import BaselineApplicationPackage
from keywords.linux.hostname_keywords import HostnameKeywords


class InterfaceMetricsCompatibilityKeywords(BaseKeyword):
    """Reuse exporter operations without manually updating the application."""

    def __init__(self, ssh_connection: SSHConnection):
        """Use the existing controller connection and exporter operations.

        Args:
            ssh_connection (SSHConnection): Active controller connection.
        """
        self.ssh_connection = ssh_connection
        self.exporter = NodeInterfaceMetricsExporterKeywords(ssh_connection)

    def validate_upgrade_releases(self, from_version: str, to_version: str) -> None:
        """Validate release syntax and forward upgrade ordering.

        Args:
            from_version (str): Installed major.minor release.
            to_version (str): Requested major.minor release.
        """
        if not all(isinstance(version, str) and re.fullmatch(r"\d+\.\d+", version) for version in (from_version, to_version)):
            raise KeywordException("Compatibility requires numeric major.minor platform releases")
        if tuple(map(int, to_version.split("."))) <= tuple(map(int, from_version.split("."))):
            raise KeywordException("Target platform release must be newer than the installed release")

    def get_baseline_package(self, release: str) -> BaselineApplicationPackage:
        """Resolve the original app archive before registering recovery or mutating.

        Args:
            release (str): Installed platform major.minor release.

        Returns:
            BaselineApplicationPackage: Exact archive path and application version.
        """
        base = PurePosixPath(ConfigurationManager.get_app_config().get_base_application_path())
        if not base.is_absolute():
            raise ValueError("base_application_path must be absolute")
        application = self.exporter.application_state()
        if application:
            version = application[0]
            artifact = str(base / f"{APPLICATION_NAME}-{version}.tgz")
        else:
            output = self.ssh_connection.send(f"find {quote(str(base))} -maxdepth 1 -type f -name '{APPLICATION_NAME}-*.tgz'")
            self.validate_success_return_code(self.ssh_connection)
            archive_listing = "\n".join(line.rstrip("\n") for line in output) if isinstance(output, list) else output
            archives = archive_listing.splitlines()
            if len(archives) != 1:
                raise ValueError("Expected exactly one bundled exporter archive")
            artifact = archives[0]
            version = PurePosixPath(artifact).name.removeprefix(f"{APPLICATION_NAME}-").removesuffix(".tgz")
        if not version.startswith(f"{release}-"):
            raise ValueError(f"Exporter baseline {version} does not match platform {release}")
        self.exporter.validate_artifact(artifact, version)
        return BaselineApplicationPackage(artifact, version)

    def validate_metrics(self, phase: str, expected_nodes: tuple[str, ...] | None = None) -> tuple[str, ...]:
        """Scrape each ready node against freshly read host PF/VF identities.

        Read from loopback on an independently verified SSH node, avoiding an
        endpoint accidentally resolving to another node. Preserve baseline node
        coverage across releases even if labels or scheduling change.

        Args:
            phase (str): Baseline, post-upgrade or post-rollback evidence label.
            expected_nodes (tuple[str, ...] | None): Baseline participating nodes.

        Returns:
            tuple[str, ...]: Verified participating node names.
        """
        pods = self.exporter.wait_ready(timeout=900)
        nodes = tuple(sorted(pods))
        if not nodes:
            raise ValueError("Exporter compatibility requires participating nodes")
        if expected_nodes is not None:
            validate_equals(nodes, expected_nodes, f"[{phase}] exporter retains baseline node coverage")
        controllers = {host.get_host_name() for host in SystemHostListKeywords(self.ssh_connection).get_controllers()}
        connections = LabConnectionKeywords()
        for hostname in nodes:
            connection = connections.get_ssh_for_hostname(hostname) if hostname in controllers else connections.get_compute_ssh(hostname)
            node_exporter = NodeInterfaceMetricsExporterKeywords(connection)
            validate_equals(HostnameKeywords(connection).get_hostname(), hostname, f"[{phase}] SSH reaches the expected exporter node")
            inventory = node_exporter.interface_inventory(connection)
            metrics = self._wait_for_metrics(node_exporter, phase, hostname)
            metrics.verify_interfaces(inventory)
            images = {item["name"]: item.get("imageID") for item in pods[hostname]["status"]["containerStatuses"]}
            get_logger().log_info(f"[{phase}] exporter metrics verified on {hostname}: interfaces={inventory}; samples={len(metrics.get_samples())}; images={images}")
        return nodes

    def _wait_for_metrics(self, node_exporter: NodeInterfaceMetricsExporterKeywords, phase: str, hostname: str) -> InterfaceMetricsOutput:
        """Wait only for the observed Kubernetes API connection-refused condition.

        Pod readiness does not establish that the exporter can reach the API
        through its Service address after activation. Other HTTP errors,
        transport failures and invalid metric evidence remain immediate errors.

        Args:
            node_exporter (NodeInterfaceMetricsExporterKeywords): Verified node-local endpoint reader.
            phase (str): Compatibility phase for diagnostics.
            hostname (str): Verified participating node identity.

        Returns:
            InterfaceMetricsOutput: Fresh successful scrape with valid samples.
        """

        def observe() -> ValidationResponse:
            response = node_exporter.read_endpoint("127.0.0.1")
            if response.get_status_code() == 500 and re.fullmatch(r'Get "https://[^/"\s]+/api/v1/pods\?[^"\s]+": dial tcp [^\s]+: connect: connection refused', response.get_body().strip()):
                get_logger().log_info(f"[{phase}] exporter on {hostname} is waiting for Kubernetes API connectivity: {response.get_body().strip()}")
                return ValidationResponse(False, None)
            if response.get_status_code() != 200:
                raise ValueError(f"Exporter metrics on {hostname} returned HTTP {response.get_status_code()}: {response.get_body()[:1000]}")
            metrics = InterfaceMetricsOutput(response.get_body())
            return ValidationResponse(True, metrics)

        return validate_equals_with_retry(observe, True, f"[{phase}] exporter serves metrics on {hostname}", timeout=300, polling_sleep_time=10)
