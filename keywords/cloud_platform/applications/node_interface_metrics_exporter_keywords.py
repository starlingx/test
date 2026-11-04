"""Shared node-interface-metrics-exporter endpoint operations."""

import ipaddress
import json
import re
import shlex
from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import uuid4

import yaml

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.cloud_platform.applications.object.exporter_http_output import ExporterHttpOutput
from keywords.cloud_platform.applications.object.exporter_workload_output import ExporterWorkloadOutput
from keywords.cloud_platform.applications.object.interface_metrics_output import InterfaceMetricsOutput
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.node.kubectl_label_node_keywords import KubectlLabelNodeKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.ip.host_interface_inventory_keywords import HostInterfaceInventoryKeywords

APPLICATION_NAME = "node-interface-metrics-exporter"


class NodeInterfaceMetricsExporterKeywords(K8sBaseKeyword):
    """Read exporter endpoints through an existing lab SSH connection."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str | None = None):
        """Initialize the exporter reader.

        Args:
            ssh_connection (SSHConnection): Connection with access to node addresses.
            kubeconfig_path (str | None): Optional controller kubeconfig path.
        """
        super().__init__(ssh_connection, kubeconfig_path)
        self.kubeconfig_path = kubeconfig_path

    def read_endpoint(self, address: str, path_segments: tuple[str, ...] = ("metrics",), method: str = "GET", timeout: int = 30) -> ExporterHttpOutput:
        """Read a node endpoint with bounded transport and encoded path segments.

        HTTP errors are returned for negative tests; connection failures raise.
        The address comes from node inventory, independently of exporter output.

        Args:
            address (str): IPv4 or IPv6 node address, without URL brackets.
            path_segments (tuple[str, ...]): Individual path segments, such as metrics/device/PF.
            method (str): HTTP method, including methods used by negative tests.
            timeout (int): Positive maximum duration of the HTTP operation in seconds.

        Returns:
            ExporterHttpOutput: HTTP status and unparsed response body.
        """
        if type(timeout) is not int or timeout <= 0:
            raise ValueError("HTTP timeout must be a positive integer")
        if method not in {"GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS"}:
            raise ValueError("Unsupported HTTP test method")
        node_ip = ipaddress.ip_address(address)
        node_url_host = f"[{node_ip}]" if node_ip.version == 6 else str(node_ip)
        path = "/".join(quote(segment, safe="") for segment in path_segments)
        url = f"http://{node_url_host}:9110/{path}"
        command = f"curl --silent --show-error --noproxy '*' --globoff --path-as-is --connect-timeout {timeout} --max-time {timeout} --request {method} --write-out '\n%{{http_code}}' -- {shlex.quote(url)}"
        output = self.ssh_connection.send(command, command_timeout=timeout + 10)
        return ExporterHttpOutput.from_curl(output, self.ssh_connection.get_return_code())

    def read_metrics(self, address: str, path_segments: tuple[str, ...] = ("metrics",)) -> InterfaceMetricsOutput:
        """Read and strictly parse a successful exporter scrape.

        Args:
            address (str): Independently discovered node IP address.
            path_segments (tuple[str, ...]): Endpoint path segments.

        Returns:
            InterfaceMetricsOutput: Nonempty parsed metric samples.
        """
        response = self.read_endpoint(address, path_segments)
        if response.get_status_code() != 200:
            raise ValueError(f"Exporter metrics returned HTTP {response.get_status_code()}")
        return InterfaceMetricsOutput(response.get_body())

    def workload(self) -> ExporterWorkloadOutput:
        """Read rendered scheduling and cross-check Kubernetes nodes with platform inventory.

        Returns:
            ExporterWorkloadOutput: Fresh workload and inventory snapshot.
        """
        resource_keywords = KubectlGetResourceKeywords(self.ssh_connection, self.kubeconfig_path)
        daemonsets = json.loads(resource_keywords.get_resource_field("daemonsets", "", "{@}", APPLICATION_NAME))["items"]
        if len(daemonsets) != 1:
            raise ValueError("Expected exactly one exporter DaemonSet")
        nodes = json.loads(resource_keywords.get_resource_field("nodes", "", "{@}"))["items"]
        inventory = {host.get_host_name() for host in SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_hosts()}
        workload = ExporterWorkloadOutput(daemonsets[0], nodes)
        if not set(workload.eligible_nodes()) <= inventory:
            raise ValueError("Exporter nodes are missing from platform host inventory")
        return workload

    def wait_ready(self, timeout: int = 300) -> dict[str, dict]:
        """Wait for complete ready coverage using fresh scheduling on every poll.

        Args:
            timeout (int): Maximum readiness polling duration in seconds.

        Returns:
            dict[str, dict]: Ready pods indexed by node.
        """

        def observe() -> ValidationResponse:
            workload = self.workload()
            label = workload.get_label_selector()
            pods = KubectlGetPodsKeywords(self.ssh_connection, self.kubeconfig_path).get_pods_json(namespace=APPLICATION_NAME, label=label).get_pod_records()
            ready_pods = workload.ready_pods(pods)
            return ValidationResponse(bool(ready_pods), ready_pods)

        return validate_equals_with_retry(observe, True, "Exporter pods ready on every eligible node", timeout=timeout, polling_sleep_time=5)

    def verify_candidate(self, version: str, images: dict[str, str]) -> dict[str, dict]:
        """Verify requested app version and immutable image identities on all nodes.

        Args:
            version (str): Explicit candidate application version.
            images (dict[str, str]): Container names mapped to expected sha256 digests.

        Returns:
            dict[str, dict]: Verified ready pods, suitable for recording evidence.
        """
        if not version or not images or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) for digest in images.values()):
            raise ValueError("Candidate version and immutable container digests are required")
        if self.application_state() != (version, "applied"):
            raise ValueError("Installed exporter does not match the applied candidate version")
        pods = self.wait_ready()
        for node, pod in pods.items():
            container_statuses_by_name = {item["name"]: item for item in pod["status"]["containerStatuses"]}
            if set(container_statuses_by_name) != set(images):
                raise ValueError(f"Candidate container set differs on {node}")
            for name, digest in images.items():
                actual_image_digest = container_statuses_by_name[name].get("imageID", "").split("@")[-1].removeprefix("containerd://").removeprefix("docker://")
                if actual_image_digest != digest:
                    raise ValueError(f"Wrong candidate image on {node}/{name}: {actual_image_digest}")
        return pods

    def interface_inventory(self, node_connection: SSHConnection) -> dict[str, dict]:
        """Read PF/VF identities from host sysfs independently of the exporter.

        Args:
            node_connection (SSHConnection): Existing SSH connection to the exact target node.

        Returns:
            dict[str, dict]: Admin-UP, non-loopback/non-veth interfaces and VF PCI identities.
        """
        return HostInterfaceInventoryKeywords(node_connection).get_interface_inventory().get_interfaces()

    def application_state(self) -> tuple[str, str] | None:
        """Read application identity without hiding CLI failures as absence.

        Returns:
            tuple[str, str] | None: Version/status or confirmed absence.
        """
        return SystemApplicationListKeywords(self.ssh_connection).get_application_state(APPLICATION_NAME)

    def user_overrides(self) -> dict:
        """Read the complete user override mapping.

        Returns:
            dict: Original Helm user values, including an empty mapping.
        """
        return SystemHelmOverrideKeywords(self.ssh_connection).get_user_override_values(APPLICATION_NAME, APPLICATION_NAME, APPLICATION_NAME)

    def set_overrides(self, values: dict) -> None:
        """Replace stored user values without merging test leftovers.

        Args:
            values (dict): Complete desired user overrides.
        """
        helm = SystemHelmOverrideKeywords(self.ssh_connection)
        if values:
            path = f"/tmp/exporter-test-{uuid4().hex}.yaml"
            try:
                self.ssh_connection.send(f"umask 077; printf %s {shlex.quote(yaml.safe_dump(values))} > {shlex.quote(path)}")
                self.validate_success_return_code(self.ssh_connection)
                helm.update_helm_override(path, APPLICATION_NAME, APPLICATION_NAME, APPLICATION_NAME, reuse_values=False)
            finally:
                self.ssh_connection.send(f"rm -f -- {shlex.quote(path)}")
                self.validate_success_return_code(self.ssh_connection)
        elif self.user_overrides():
            helm.delete_system_helm_override(APPLICATION_NAME, APPLICATION_NAME, APPLICATION_NAME)
        if self.user_overrides() != values:
            raise ValueError("Exporter user overrides did not match requested values")

    def validate_artifact(self, artifact: str, version: str) -> None:
        """Verify an explicit local application archive before any mutation.

        Args:
            artifact (str): Absolute controller path to a staged archive.
            version (str): Expected archive application version.
        """
        if not artifact or not version or not PurePosixPath(artifact).is_absolute() or any(char in artifact for char in "*?[]\n\r"):
            raise ValueError("An exact absolute artifact path and version are required")
        output = self.ssh_connection.send(f"tar -tf {shlex.quote(artifact)}")
        self.validate_success_return_code(self.ssh_connection)
        members = "\n".join(line.rstrip("\n") for line in output).splitlines() if isinstance(output, list) else output.splitlines()
        metadata = [member for member in members if member in ("metadata.yaml", "./metadata.yaml")]
        if len(metadata) != 1:
            raise ValueError("Archive requires exactly one root metadata.yaml")
        output = self.ssh_connection.send(f"tar -xOf {shlex.quote(artifact)} {shlex.quote(metadata[0])}")
        self.validate_success_return_code(self.ssh_connection)
        content = "\n".join(line.rstrip("\n") for line in output) if isinstance(output, list) else output
        values = yaml.safe_load(content)
        if not isinstance(values, dict) or values.get("app_name") != APPLICATION_NAME or str(values.get("app_version")) != version:
            raise ValueError("Exporter archive identity differs from the requested version")

    def upload(self, artifact: str, version: str) -> None:
        """Upload a staged candidate or recovery archive using existing ACE keywords.

        Args:
            artifact (str): Exact controller-local archive.
            version (str): Expected application version.
        """
        self.validate_artifact(artifact, version)
        request = SystemApplicationUploadInput()
        request.set_app_name(APPLICATION_NAME)
        request.set_tar_file_path(shlex.quote(artifact))
        SystemApplicationUploadKeywords(self.ssh_connection).system_application_upload(request)
        if self.application_state() != (version, "uploaded"):
            raise ValueError("Uploaded exporter version differs from requested version")

    def apply(self) -> None:
        """Apply through the shared application keyword and bounded status polling."""
        SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply(APPLICATION_NAME)

    def remove(self) -> None:
        """Remove through the shared application keyword."""
        request = SystemApplicationRemoveInput()
        request.set_app_name(APPLICATION_NAME)
        SystemApplicationRemoveKeywords(self.ssh_connection).system_application_remove(request)

    def delete(self) -> None:
        """Delete an uploaded application through the shared keyword."""
        request = SystemApplicationDeleteInput()
        request.set_app_name(APPLICATION_NAME)
        SystemApplicationDeleteKeywords(self.ssh_connection).get_system_application_delete(request)

    def exporter_labels(self) -> dict[str, str | None]:
        """Capture only the node label owned by the exporter lifecycle.

        Returns:
            dict[str, str | None]: Node to original label value or absence.
        """
        nodes = json.loads(KubectlGetResourceKeywords(self.ssh_connection, self.kubeconfig_path).get_resource_field("nodes", "", "{@}"))["items"]
        return {node["metadata"]["name"]: node["metadata"].get("labels", {}).get("starlingx.io/interface-metrics") for node in nodes}

    def restore_labels(self, labels: dict[str, str | None]) -> None:
        """Restore exporter labels without replacing unrelated node labels.

        Args:
            labels (dict[str, str | None]): Original exporter label snapshot.
        """
        current = self.exporter_labels()
        if current.keys() != labels.keys():
            raise ValueError("Node inventory changed; cannot restore exporter labels safely")
        for node, value in labels.items():
            if value != current[node]:
                labels_api = KubectlLabelNodeKeywords(self.ssh_connection, self.kubeconfig_path)
                if value is None:
                    labels_api.remove_label(shlex.quote(node), "starlingx.io/interface-metrics")
                else:
                    labels_api.label_node(shlex.quote(node), "starlingx.io/interface-metrics", shlex.quote(value))
        if self.exporter_labels() != labels:
            raise ValueError("Exporter labels were not restored")

    def chart_enabled(self) -> bool:
        """Read the supported chart enablement attribute.

        Returns:
            bool: Effective chart enablement.
        """
        attributes = SystemHelmOverrideKeywords(self.ssh_connection).get_system_helm_override_show(APPLICATION_NAME, APPLICATION_NAME, APPLICATION_NAME).get_helm_override_show().get_attributes()
        attributes = yaml.safe_load(attributes) if isinstance(attributes, str) else attributes
        if not isinstance(attributes, dict) or set(attributes) - {"enabled"}:
            raise ValueError("Unsupported exporter chart attributes")
        enabled = attributes.get("enabled", True)
        if type(enabled) is not bool:
            raise ValueError("Invalid chart enablement attribute")
        return enabled

    def set_chart_enabled(self, enabled: bool) -> None:
        """Restore chart enablement through the existing Helm attribute keyword.

        Args:
            enabled (bool): Desired chart enablement.
        """
        if self.chart_enabled() != enabled:
            SystemHelmChartAttributeModifyKeywords(self.ssh_connection).helm_chart_attribute_modify_enabled(str(enabled).lower(), APPLICATION_NAME, APPLICATION_NAME, APPLICATION_NAME)
        if self.chart_enabled() != enabled:
            raise ValueError("Chart enablement was not restored")

    def discover_pods(self) -> list[dict]:
        """Read exporter namespace pods for orphan detection and inactive cleanup.

        Returns:
            list[dict]: All pods, including terminating or unready resources.
        """
        return KubectlGetPodsKeywords(self.ssh_connection, self.kubeconfig_path).get_pods_json(namespace=APPLICATION_NAME).get_pod_records()

    def wait_absent(self, timeout: int = 180) -> None:
        """Wait until no exporter namespace pods remain after removal.

        Args:
            timeout (int): Maximum pod deletion wait in seconds.
        """
        validate_equals_with_retry(lambda: not self.discover_pods(), True, "Exporter pods removed", timeout=timeout, polling_sleep_time=5)
