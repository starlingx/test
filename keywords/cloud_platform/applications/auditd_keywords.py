"""Shared auditd operations; event correlation belongs to the consuming event suite."""

import re
from collections.abc import Callable, Generator
from contextlib import contextmanager
from shlex import quote
from typing import TypeVar
from uuid import uuid4

import yaml

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from framework.validation.validation import validate_equals_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.cloud_platform.applications.object.audit_event_output import AuditEventOutput
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_abort_keywords import SystemApplicationAbortKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

T = TypeVar("T")


def output_text(output: str | list[str]) -> str:
    """Normalize SSH output without joining adjacent lines.

    Args:
        output (str | list[str]): Framework command output.

    Returns:
        str: Normalized text.
    """
    return "\n".join(line.rstrip("\n") for line in output) if isinstance(output, list) else output


def parse_audit_config(text: str) -> dict[str, str]:
    """Parse auditd.conf, rejecting empty, duplicate or malformed settings.

    Args:
        text (str): Effective auditd configuration.

    Returns:
        dict[str, str]: Settings with literal value content preserved; comment lines omitted.
    """
    settings = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", key) or not value or key in settings:
            raise KeywordException(f"Malformed or duplicate audit setting on line {number}: {line!r}")
        settings[key] = value
    if not settings:
        raise KeywordException("No audit configuration settings returned")
    return settings


def wait_for_audit(probe: Callable[[], T], description: str, timeout: float = 120, interval: float = 5) -> T:
    """Poll for nonempty evidence, propagating command and parser failures.

    A probe returns a false value only for a valid but not-yet-ready observation.
    Event consumers can supply a correlation probe; this function does not define
    what constitutes a fresh event.

    Args:
        probe (Callable[[], T]): Observation to repeat.
        description (str): Diagnostic context, including host when applicable.
        timeout (float): Maximum polling duration in seconds.
        interval (float): Delay between probes in seconds.

    Returns:
        T: First truthy observation.
    """
    if timeout < 0 or interval <= 0:
        raise ValueError("timeout must be nonnegative and interval must be positive")
    last_evidence = None

    def observation() -> ValidationResponse:
        nonlocal last_evidence
        last_evidence = probe()
        return ValidationResponse(bool(last_evidence), last_evidence)

    try:
        return validate_equals_with_retry(observation, True, description, timeout=timeout, polling_sleep_time=interval)
    except TimeoutError as error:
        raise KeywordException(f"Timed out waiting for {description}; last evidence: {last_evidence!r}") from error


class AuditdKeywords(K8sBaseKeyword):
    """Audit operations using the existing platform, Kubernetes and SSH keywords."""

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str = None) -> None:
        """Initialize audit operations and their operation-scoped session state.

        Args:
            ssh_connection (SSHConnection): Connection to the active controller.
            kubeconfig_path (str): Optional kubeconfig path on the controller.
        """
        super().__init__(ssh_connection, kubeconfig_path)
        self.kubeconfig_path = kubeconfig_path
        self._node_connections: dict[str, SSHConnection] | None = None
        self._node_controllers: set[str] | None = None
        self._last_readiness_reason = "no pod observation completed"

    def command(self, command: str) -> str:
        """Execute a controller command and check its status before parsing.

        Args:
            command (str): Fully quoted shell command.

        Returns:
            str: Command output.
        """
        output = self.ssh_connection.send(command)
        try:
            self.validate_success_return_code(self.ssh_connection)
        except AssertionError as error:
            raise KeywordException(f"Audit command failed: {command}; {output_text(output)}; {error}") from error
        return output_text(output)

    def participating_hosts(self) -> tuple[str, ...]:
        """Discover every controller and worker, requiring a healthy baseline.

        Returns:
            tuple[str, ...]: Unique inventory host names.
        """
        hosts = SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_hosts()
        selected = [host for host in hosts if host.get_personality() in ("controller", "worker")]
        if not selected:
            raise KeywordException("No participating controllers/workers in inventory")
        for host in selected:
            if (host.get_administrative(), host.get_operational(), host.get_availability()) != ("unlocked", "enabled", "available"):
                raise KeywordException(f"Audit baseline requires unlocked/enabled/available host: {host.get_host_name()}")
        names = tuple(host.get_host_name() for host in selected)
        if len(set(names)) != len(names):
            raise KeywordException(f"Duplicate inventory hosts: {names}")
        return names

    def active_controller(self) -> str:
        """Read the active controller identity.

        Returns:
            str: Active controller host name.
        """
        return SystemHostListKeywords(self.ssh_connection).get_active_controller().get_host_name()

    def restore_controller(self, hostname: str) -> None:
        """Restore controller role and verify the result, including simplex.

        Args:
            hostname (str): Original active controller.
        """
        self.invalidate_node_sessions()
        if self.active_controller() != hostname:
            SystemHostSwactKeywords(self.ssh_connection).ensure_controller_is_active(hostname)
        if self.active_controller() != hostname:
            raise KeywordException(f"Could not restore active controller {hostname}")

    def kernel_parameter(self) -> str:
        """Read the supported global audit service parameter.

        Returns:
            str: Explicit configured value, zero or one.
        """
        parameters = SystemServiceParameterKeywords(self.ssh_connection).list_service_parameters("platform", "kernel").get_parameters()
        values = [parameter.get_value() for parameter in parameters if parameter.get_name() == "audit"]
        if len(values) != 1 or values[0] not in ("0", "1"):
            raise KeywordException(f"Expected one global platform/kernel/audit parameter (0 or 1), found {values}")
        return values[0]

    @contextmanager
    def node_session(self) -> Generator[None, None, None]:
        """Reuse node SSH connections within a read operation and close them on exit.

        Nested read operations share the outer session. No connections survive
        the outer operation, so reboots, swact and application changes performed
        between operations cannot reuse a previous session.

        Yields:
            None: Scope in which node commands share connections.
        """
        if self._node_connections is not None:
            yield
            return
        self._node_connections = {}
        self._node_controllers = None
        failure = None
        try:
            yield
        except Exception as error:
            failure = error
            raise
        finally:
            connections = self._node_connections
            self._node_connections = None
            self._node_controllers = None
            errors = []
            for connection in connections.values():
                try:
                    self._close_node_connection(connection)
                except Exception as error:
                    errors.append(error)
            if errors:
                raise ExceptionGroup("Audit SSH session cleanup failed", ([failure] if failure else []) + errors)

    def invalidate_node_sessions(self) -> None:
        """Drop operation connections before a disruptive platform action."""
        cache = self._node_connections
        if cache is None:
            return
        connections = list(cache.values())
        cache.clear()
        self._node_controllers = None
        errors = []
        for connection in connections:
            try:
                self._close_node_connection(connection)
            except Exception as error:
                errors.append(error)
        if errors:
            raise ExceptionGroup("Audit SSH invalidation failed", errors)

    def _close_node_connection(self, connection: SSHConnection) -> None:
        """Close a node session and remove its entry from the framework manager.

        Args:
            connection (SSHConnection): Connection owned by this audit operation.
        """
        name = connection.get_name()
        managed = SSHConnectionManager.get_ssh_connection(name)
        if managed is None:
            return  # Already released by the framework.
        if managed is not connection:
            raise KeywordException(f"SSH manager entry {name} belongs to another connection")
        SSHConnectionManager.remove_ssh_connection(name)

    def node_command(self, hostname: str, command: str) -> str:
        """Run a checked node command, reusing only the current operation's session.

        Args:
            hostname (str): Inventory node name.
            command (str): Quoted node-local command.

        Returns:
            str: Node command output.
        """
        with self.node_session():
            cache = self._node_connections
            connection = cache.get(hostname)
            try:
                if connection is None:
                    if self._node_controllers is None:
                        controllers = SystemHostListKeywords(self.ssh_connection).get_controllers()
                        self._node_controllers = {host.get_host_name() for host in controllers}
                    connections = LabConnectionKeywords()
                    connection = connections.get_ssh_for_hostname(hostname) if hostname in self._node_controllers else connections.get_compute_ssh(hostname)
                    cache[hostname] = connection
                    identity = connection.send("hostname")
                    self.validate_success_return_code(connection)
                    if output_text(identity).strip() != hostname:
                        raise KeywordException(f"Expected SSH node {hostname}, received {output_text(identity)!r}")
                output = connection.send(command)
                try:
                    self.validate_success_return_code(connection)
                except AssertionError as error:
                    raise KeywordException(f"Audit command failed on {hostname}: {command}; {output_text(output)}; {error}") from error
                return output_text(output)
            except Exception as command_error:
                cache.pop(hostname, None)
                try:
                    if connection is not None:
                        self._close_node_connection(connection)
                except Exception as cleanup_error:
                    raise ExceptionGroup("Audit node command and connection cleanup failed", [command_error, cleanup_error]) from command_error
                raise

    def boot_audit(self, hostname: str) -> str:
        """Read the exact kernel audit argument on a named node.

        Args:
            hostname (str): Inventory node.

        Returns:
            str: Explicit audit boot setting.
        """
        tokens = self.node_command(hostname, "cat /proc/cmdline").split()
        values = [token.partition("=")[2] for token in tokens if token.startswith("audit=")]
        if len(values) != 1 or values[0] not in ("0", "1"):
            raise KeywordException(f"Missing, ambiguous or invalid audit boot argument on {hostname}: {values}")
        return values[0]

    def set_kernel_audit(self, value: str, hosts: tuple[str, ...]) -> None:
        """Apply the supported service parameter and reboot only mismatching hosts.

        Recovery also unlocks a host left locked by an interrupted setup.

        Args:
            value (str): Desired zero or one value.
            hosts (tuple[str, ...]): Complete participating host inventory.
        """
        if value not in ("0", "1") or not hosts:
            raise ValueError("An explicit audit value and nonempty host inventory are required")
        self.invalidate_node_sessions()
        service = SystemServiceParameterKeywords(self.ssh_connection)
        if self.kernel_parameter() != value:
            service.modify_service_parameter("platform", "kernel", "audit", value)
        # Always apply: a previous modify may have succeeded before apply failed.
        service.apply_service_parameters("platform")
        locks = SystemHostLockKeywords(self.ssh_connection)
        errors = []
        for hostname in hosts:
            try:
                self.invalidate_node_sessions()
                locks.ensure_host_unlocked(hostname)
                self.invalidate_node_sessions()
                if self.boot_audit(hostname) != value:
                    self.invalidate_node_sessions()
                    SystemHostSwactKeywords(self.ssh_connection).swact_if_active(hostname)
                    locks.lock_host(hostname)
                    locks.unlock_host(hostname)
                    self.invalidate_node_sessions()
                if self.boot_audit(hostname) != value:
                    raise KeywordException(f"audit={value} was not effective after reboot on {hostname}")
            except Exception as error:
                errors.append(KeywordException(f"Kernel audit recovery on {hostname}: {error}"))
        if errors:
            raise ExceptionGroup("Could not establish the requested audit boot state on every host", errors)

    def discover_pods(self) -> list[dict]:
        """Discover all audit pods, including Pending, Failed and terminating pods.

        Reuse the shared bounded read retry for API outages during activation,
        while retaining complete JSON readiness evidence.

        Returns:
            list[dict]: Kubernetes pod records.
        """
        pods = KubectlGetPodsKeywords(self.ssh_connection, self.kubeconfig_path)
        return pods.get_pods_with_retry(reader=lambda: pods.get_pods_json(namespace="kube-system", label="app=auditd")).get_pod_records()

    def ready_pods(self, hosts: tuple[str, ...]) -> dict[str, dict]:
        """Discover and validate exact audit pod coverage, including unhealthy pods.

        Args:
            hosts (tuple[str, ...]): Expected inventory, independent of discovery.

        Returns:
            dict[str, dict]: Ready pods keyed by node, or empty during convergence.
        """
        if not hosts or len(hosts) != len(set(hosts)):
            raise ValueError("Expected unique, nonempty audit host inventory")
        return self._validate_pods(hosts, self.discover_pods())

    def _validate_pods(self, hosts: tuple[str, ...], records: list[dict]) -> dict[str, dict]:
        """Validate a single observation without querying Kubernetes again.

        An assigned node outside the inventory fails immediately. Unscheduled,
        terminating and duplicate pods remain retryable during rollout.

        Args:
            hosts (tuple[str, ...]): Complete expected node inventory.
            records (list[dict]): One Kubernetes pod-list snapshot.

        Returns:
            dict[str, dict]: Complete ready coverage, or empty during convergence.
        """
        if not hosts or len(hosts) != len(set(hosts)):
            raise ValueError("Expected unique, nonempty audit host inventory")
        result, reasons = {}, []
        for pod in records:
            node = pod.get("spec", {}).get("nodeName")
            metadata, status = pod.get("metadata", {}), pod.get("status", {})
            name = metadata.get("name", "<unnamed>")
            if node and node not in hosts:
                raise KeywordException(f"Audit pod {name} is assigned to unexpected node {node}; expected {hosts}")
            containers = pod.get("spec", {}).get("containers", [])
            statuses = status.get("containerStatuses", [])
            expected = {container.get("name") for container in containers}
            observed = {container.get("name") for container in statuses}
            ready = any(condition.get("type") == "Ready" and condition.get("status") == "True" for condition in status.get("conditions", []))
            if not node:
                reasons.append(f"{name}: not scheduled")
            elif node in result:
                reasons.append(f"{name}: duplicate pod on {node} during rollout")
            if not metadata.get("name") or not metadata.get("uid") or metadata.get("deletionTimestamp"):
                reasons.append(f"{name} on {node}: missing identity or terminating")
            if status.get("phase") != "Running" or not ready or not expected or None in expected or expected != observed or len(statuses) != len(expected):
                reasons.append(f"{name} on {node}: phase={status.get('phase')}, Ready={ready}, containers={sorted(str(item) for item in observed)}/{sorted(str(item) for item in expected)}")
            if not all(container.get("ready") is True and "running" in container.get("state", {}) for container in statuses):
                reasons.append(f"{name} on {node}: containers not running/ready")
            if node:
                result[node] = pod
        missing = set(hosts) - set(result)
        if missing:
            reasons.append(f"missing audit pods on {sorted(missing)}")
        if reasons:
            self._last_readiness_reason = "; ".join(reasons)
            get_logger().log_info(f"Audit pods not ready: {self._last_readiness_reason}")
            return {}
        return result

    def wait_ready(self, hosts: tuple[str, ...], timeout: float = 180, interval: float = 5) -> dict[str, dict]:
        """Wait for exact coverage and report the observed pods on timeout.

        Args:
            hosts (tuple[str, ...]): Complete expected node inventory.
            timeout (float): Readiness deadline in seconds.
            interval (float): Poll interval in seconds.

        Returns:
            dict[str, dict]: Ready audit pods by node.
        """
        self._last_readiness_reason = "no pod observation completed"
        try:
            return wait_for_audit(lambda: self.ready_pods(hosts), f"audit pods on {hosts}", timeout, interval)
        except KeywordException as error:
            raise KeywordException(f"{error}; last readiness observation: {self._last_readiness_reason}") from error

    def pod_command(self, hostname: str, hosts: tuple[str, ...], command: str, pods: dict[str, dict] | None = None, ignore_error: bool = False) -> str:
        """Run a checked command in the audit container on an exact node.

        Args:
            hostname (str): Required pod node.
            hosts (tuple[str, ...]): Complete expected inventory.
            command (str): Quoted command inside the container.
            pods (dict[str, dict] | None): Validated snapshot for this operation; rediscover when omitted.
            ignore_error (bool): Leave return-code validation to the caller's output parser.

        Returns:
            str: Container command output.
        """
        if hostname not in hosts:
            raise ValueError(f"Unknown participating host: {hostname}")
        if pods is None:
            pods = self.wait_ready(hosts)
        if set(pods) != set(hosts) or not self._validate_pods(hosts, list(pods.values())) or any(pods[node].get("spec", {}).get("nodeName") != node for node in hosts):
            raise KeywordException("Invalid audit pod snapshot for the requested host inventory")
        pod = pods[hostname]
        containers = [container["name"] for container in pod["spec"]["containers"]]
        if "auditd" not in containers:
            raise KeywordException(f"No auditd container on {hostname}: {containers}")
        output = KubectlExecInPodsKeywords(self.ssh_connection, self.kubeconfig_path).run_pod_exec_cmd(quote(pod["metadata"]["name"]), command, options="-n kube-system -c auditd", ignore_error=ignore_error)
        return output_text(output)

    def verify_runtime(self, hosts: tuple[str, ...]) -> None:
        """Verify boot enablement and a live audit daemon on every node.

        Args:
            hosts (tuple[str, ...]): Complete expected inventory.
        """
        pods = self.wait_ready(hosts)
        with self.node_session():
            for hostname in hosts:
                if self.boot_audit(hostname) != "1":
                    raise KeywordException(f"audit=1 missing on {hostname}")
                self._verify_daemon(hostname, hosts, pods)

    def _verify_daemon(self, hostname: str, hosts: tuple[str, ...], pods: dict[str, dict]) -> None:
        """Verify daemon evidence on one node from the current readiness snapshot.

        Args:
            hostname (str): Node being checked.
            hosts (tuple[str, ...]): Expected inventory.
            pods (dict[str, dict]): Current ready pod snapshot.
        """
        status = self.pod_command(hostname, hosts, "auditctl -s", pods=pods)
        enabled = re.findall(r"^enabled\s+(\d+)\s*$", status, re.MULTILINE)
        pid = re.findall(r"^pid\s+(\d+)\s*$", status, re.MULTILINE)
        if enabled != ["1"] or len(pid) != 1 or int(pid[0]) <= 0:
            raise KeywordException(f"Audit daemon is disabled, immutable or absent on {hostname}: {status}")

    def effective_settings(self, hosts: tuple[str, ...]) -> dict[str, dict]:
        """Capture effective configuration and rules for restoration verification.

        Args:
            hosts (tuple[str, ...]): Complete expected inventory.

        Returns:
            dict[str, dict]: Configuration and normalized active rules per node.
        """
        pods = self.wait_ready(hosts)
        result = {}
        for hostname in hosts:
            config = parse_audit_config(self.pod_command(hostname, hosts, "cat /etc/audit/auditd.conf", pods=pods))
            rules = self.pod_command(hostname, hosts, "auditctl -l", pods=pods).strip()
            if not rules:
                raise KeywordException(f"Empty auditctl rule evidence on {hostname}")
            result[hostname] = {"config": config, "rules": rules.splitlines()}
        return result

    def restart_pod(self, hostname: str, hosts: tuple[str, ...], timeout: float = 180) -> None:
        """Replace one pod and require a new UID and functional daemon.

        Args:
            hostname (str): Node whose audit pod is restarted.
            hosts (tuple[str, ...]): Complete inventory.
            timeout (float): Replacement deadline in seconds.
        """
        self.invalidate_node_sessions()
        original = self.wait_ready(hosts)[hostname]
        KubectlDeletePodsKeywords(self.ssh_connection, self.kubeconfig_path).delete_pod(original["metadata"]["name"], "kube-system")

        def replacement() -> dict:
            pods = self.ready_pods(hosts)
            return pods if pods and pods[hostname]["metadata"]["uid"] != original["metadata"]["uid"] else {}

        wait_for_audit(replacement, f"replacement audit pod on {hostname}", timeout)
        self.verify_runtime(hosts)

    def application_state(self) -> tuple[str, str] | None:
        """Read app version/status without treating CLI errors as absence.

        Returns:
            tuple[str, str] | None: Version and status, or confirmed absence.
        """
        apps = SystemApplicationListKeywords(self.ssh_connection).get_system_application_list()
        if not apps.application_exists("auditd"):
            return None
        app = apps.get_application("auditd")
        return app.get_version(), app.get_status()

    def user_overrides(self) -> dict:
        """Read the entire Helm user override mapping.

        Returns:
            dict: User overrides, preserving empty versus nonempty values.
        """
        raw = SystemHelmOverrideKeywords(self.ssh_connection).get_system_helm_override_show("auditd", "auditd", "kube-system").get_helm_override_show().get_user_overrides()
        values = yaml.safe_load(raw) if isinstance(raw, str) else raw
        if values is None or values == "None":
            return {}
        if not isinstance(values, dict):
            raise KeywordException(f"Invalid audit user override mapping: {values!r}")
        return values

    def upload(self, artifact: str, version: str) -> None:
        """Upload an exact artifact and verify its version.

        Args:
            artifact (str): Absolute controller path, without glob expansion.
            version (str): Expected application version.
        """
        self.invalidate_node_sessions()
        request = SystemApplicationUploadInput()
        request.set_app_name("auditd")
        request.set_tar_file_path(quote(artifact))
        SystemApplicationUploadKeywords(self.ssh_connection).system_application_upload(request)
        if self.application_state() != (version, "uploaded"):
            raise KeywordException(f"Uploaded audit artifact did not provide {version}")

    def apply(self) -> None:
        """Apply auditd and wait through the existing application keyword."""
        self.invalidate_node_sessions()
        SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply("auditd")

    def remove(self) -> None:
        """Remove auditd with bounded application status tracking."""
        self.invalidate_node_sessions()
        request = SystemApplicationRemoveInput()
        request.set_app_name("auditd")
        SystemApplicationRemoveKeywords(self.ssh_connection).system_application_remove(request)

    def delete(self) -> None:
        """Delete an uploaded audit application using the existing keyword."""
        self.invalidate_node_sessions()
        request = SystemApplicationDeleteInput()
        request.set_app_name("auditd")
        SystemApplicationDeleteKeywords(self.ssh_connection).get_system_application_delete(request)

    def combined_config(self) -> dict[str, str]:
        """Read the persistent Helm configuration to reject unrecoverable drift.

        Returns:
            dict[str, str]: Parsed persistent auditd.conf settings.
        """
        raw = SystemHelmOverrideKeywords(self.ssh_connection).get_system_helm_override_show("auditd", "auditd", "kube-system").get_helm_override_show().get_combined_overrides()
        values = yaml.safe_load(raw) if isinstance(raw, str) else raw
        if not isinstance(values, dict) or not isinstance(values.get("auditdconf"), str):
            raise KeywordException("Combined Helm overrides do not contain auditdconf")
        return parse_audit_config(values["auditdconf"])

    def restore_rules(self, hosts: tuple[str, ...], effective: dict) -> None:
        """Restore captured runtime rules without deleting audit logs.

        Args:
            hosts (tuple[str, ...]): Original node inventory.
            effective (dict): Original effective configuration/rules by node.
        """
        pods = self.wait_ready(hosts)
        errors = []
        for hostname in hosts:
            try:
                rules = effective[hostname]["rules"]
                current = self.pod_command(hostname, hosts, "auditctl -l", pods=pods).strip().splitlines()
                if current == rules:
                    continue
                content = "-D\n" + "\n".join(rule for rule in rules if rule != "No rules") + "\n"
                path = f"/tmp/auditd-test-{uuid4().hex}.rules"
                try:
                    script = f"umask 077; printf %s {quote(content)} > {quote(path)}"
                    self.pod_command(hostname, hosts, f"sh -c {quote(script)}", pods=pods)
                    self.pod_command(hostname, hosts, f"auditctl -R {quote(path)}", pods=pods)
                finally:
                    self.pod_command(hostname, hosts, f"rm -f -- {quote(path)}", pods=pods)
            except Exception as error:
                errors.append(KeywordException(f"Rule restoration on {hostname}: {error}"))
        if errors:
            raise ExceptionGroup("Audit rule restoration failed", errors)

    def settle_application(self) -> None:
        """Abort an interrupted operation and wait for a recoverable terminal state."""
        current = self.application_state()
        if current and current[1] in ("uploading", "applying", "updating", "removing"):
            SystemApplicationAbortKeywords(self.ssh_connection).system_application_abort("auditd")
        if current:
            terminal = ["uploaded", "applied", "upload-failed", "apply-failed", "remove-failed", "update-failed"]
            SystemApplicationListKeywords(self.ssh_connection).validate_app_status_in_list("auditd", terminal, timeout=300, polling_sleep_time=5)

    def search_syscall_events(self, hostname: str, hosts: tuple[str, ...], key: str, syscall: str) -> AuditEventOutput:
        """Read interpreted records, treating only an explicit no-match as pending.

        Args:
            hostname (str): Node whose audit container supplies the log.
            hosts (tuple[str, ...]): Complete expected inventory.
            key (str): Unique action key.
            syscall (str): Syscall name to interpret and select.

        Returns:
            AuditEventOutput: Parsed records, empty when no event is recorded yet.
        """
        # Force file input because kubectl exec supplies a pipe for stdin.
        search = f"env LC_ALL=C ausearch --input-logs --interpret -k {quote(key)} -sc {quote(syscall)}"
        output = self.pod_command(hostname, hosts, search, ignore_error=True)
        records = AuditEventOutput(output, self.ssh_connection.get_return_code())
        if records.diagnostics:
            get_logger().log_info(f"Ignored audit configuration diagnostics on {hostname}: {records.diagnostics}")
        return records
