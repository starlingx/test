"""Exporter compatibility wiring, independent evidence and recovery boundaries."""

from contextlib import ExitStack
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock, NonCallableMock, patch

import pytest

from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords import NodeInterfaceMetricsExporterKeywords
from keywords.cloud_platform.applications.object.exporter_http_output import ExporterHttpOutput
from keywords.cloud_platform.upgrade.interface_metrics_compatibility_keywords import InterfaceMetricsCompatibilityKeywords
from keywords.cloud_platform.upgrade.object.baseline_application_package import BaselineApplicationPackage

TEST_MODULE = "testcases.cloud_platform.upgrade.app_compat.test_interface_metrics_upgrade_compat"
KEYWORDS_MODULE = "keywords.cloud_platform.upgrade.interface_metrics_compatibility_keywords"
APP = "node-interface-metrics-exporter"


@pytest.fixture(autouse=True)
def configure_keyword_dependencies():
    """Supply framework logging and kubeconfig for isolated keyword tests."""
    with patch("keywords.base_keyword.get_logger"), patch("config.configuration_manager.ConfigurationManager.get_k8s_config", return_value=Mock(get_kubeconfig=lambda: "/etc/kubernetes/admin.conf")):
        yield


def create_compatibility_keywords(exporter):
    """Construct the keyword through its SSH API with controlled exporter operations."""
    with patch(f"{KEYWORDS_MODULE}.NodeInterfaceMetricsExporterKeywords", return_value=exporter):
        return InterfaceMetricsCompatibilityKeywords(exporter.ssh_connection)


class CompatibilityRun:
    """Execute production orchestration with controlled platform transitions."""

    def __init__(self, release="26.03", status=None, failure=None):
        self.release = release
        self.original_release = release
        self.deployment = ""
        self.version = f"{release}-51"
        self.application = (self.version, status) if status else None
        self.failure = failure
        self.calls = []
        self.finalizers = []
        self.nodes = ("controller-0", "worker-0")
        self.exporter = NonCallableMock(spec=NodeInterfaceMetricsExporterKeywords)
        self.exporter.application_state.side_effect = lambda: self.application
        self.exporter.upload.side_effect = lambda *args: self.set_application("uploaded")
        self.exporter.apply.side_effect = lambda: self.set_application("applied")
        self.deploy = Mock()
        self.deploy.get_running_release.side_effect = lambda: self.release
        self.deploy.get_current_deploy_state.side_effect = lambda: self.deployment
        self.driver = Mock()
        self.driver.upgrade_platform_in_order.side_effect = self.upgrade
        self.driver.rollback_platform_in_order.side_effect = self.rollback
        self.health = Mock()
        self.health.get_app_version.side_effect = lambda app: self.application[0]
        self.health.get_app_or_deploy_alarm_count.return_value = 0
        self.compatibility = Mock()
        self.compatibility.validate_upgrade_releases.side_effect = create_compatibility_keywords(Mock()).validate_upgrade_releases
        self.compatibility.get_baseline_package.return_value = BaselineApplicationPackage("/baseline.tgz", self.version)
        self.compatibility.validate_metrics.side_effect = self.scrape
        self.state = Mock()
        self.state.capture.side_effect = lambda register, artifact: register(lambda: self.calls.append("restore app"))
        self.recovery = Mock()
        self.recovery.restore_to_release.side_effect = self.recover
        self.preparation = Mock()
        self.preparation.prepare.side_effect = self.prepare

    def set_application(self, status):
        """Model setup mutation and a lost reply after upload."""
        self.application = (self.version, status)
        if self.failure == "upload":
            raise RuntimeError("upload response lost")

    def prepare(self, target):
        """Ensure recovery precedes platform setup."""
        assert len(self.finalizers) == 2
        if self.failure == "prepare":
            raise RuntimeError("preparation failed")

    def scrape(self, phase, expected_nodes=None):
        """Require real production calls at all three phases."""
        assert self.application[1] == "applied"
        assert expected_nodes == (None if phase == "pre" else self.nodes)
        self.calls.append(phase)
        if self.failure == phase:
            raise RuntimeError("scrape failed")
        return self.nodes

    def upgrade(self, deploy, target, leave_at_activate_done):
        """Simulate automatic update only after a baseline scrape."""
        assert deploy is self.deploy and leave_at_activate_done
        assert self.calls[-1] == "pre"
        self.preparation.require_precheck.assert_called_once_with(target)
        self.release = target
        self.deployment = "deploy-activate-done"
        self.application = (f"{target}-56", "applied")

    def rollback(self, deploy):
        """Return the baseline, optionally with a wrong application build."""
        assert self.calls[-1] == "post-upgrade"
        self.release = self.original_release
        self.deployment = ""
        self.application = (self.version if self.failure != "wrong build" else f"{self.original_release}-99", "applied")

    def recover(self, release):
        """Retain outstanding deployment when recovery fails."""
        self.calls.append("restore release")
        if self.failure != "recovery":
            self.release, self.deployment = release, ""

    def run(self, target="26.10"):
        """Invoke the actual pytest case with isolated collaborators."""
        module = import_module(TEST_MODULE)
        with ExitStack() as stack:
            for name, instance in {
                "NodeInterfaceMetricsExporterKeywords": self.exporter,
                "NodeInterfaceMetricsExporterState": self.state,
                "InterfaceMetricsCompatibilityKeywords": self.compatibility,
                "SoftwareDeploySequenceKeywords": self.deploy,
                "StandardPlatformUpgradeKeywords": self.driver,
                "UpgradeRecoveryKeywords": self.recovery,
                "ApplicationHealthKeywords": self.health,
                "PlatformUpgradePreparationKeywords": self.preparation,
            }.items():
                stack.enter_context(patch.object(module, name, return_value=instance))
            stack.enter_context(patch.object(module, "LabConnectionKeywords"))
            stack.enter_context(patch.object(module, "get_logger"))
            stack.enter_context(patch("framework.validation.validation.get_logger"))
            stack.enter_context(patch.object(module.ConfigurationManager, "get_app_upgrade_compat_config", return_value=Mock(get_to_version=lambda: target)))
            module.test_interface_metrics_upgrade_rollback(SimpleNamespace(addfinalizer=self.finalizers.append))

    def teardown(self):
        """Run pytest finalizers in reverse registration order."""
        for finalize in reversed(self.finalizers):
            finalize()


@pytest.mark.parametrize("release", ["25.09", "26.03"])
@pytest.mark.parametrize("status", [None, "uploaded", "applied"])
def test_round_trip_reuses_state_and_platform_drivers(release, status):
    """All supported original states get three scrapes and ordered recovery."""
    run = CompatibilityRun(release, status)
    run.run()
    run.teardown()
    assert run.calls == ["pre", "post-upgrade", "post-rollback", "restore release", "restore app"]
    assert run.exporter.upload.call_count == (status is None)
    assert run.exporter.apply.call_count == (status != "applied")


@pytest.mark.parametrize("failure", ["prepare", "upload", "pre", "post-upgrade", "post-rollback"])
def test_partial_failure_has_ordered_recovery(failure):
    """Setup and functional failures preserve platform-first cleanup."""
    run = CompatibilityRun(failure=failure)
    with pytest.raises(RuntimeError):
        run.run()
    run.teardown()
    assert run.calls[-2:] == ["restore release", "restore app"]


def test_incomplete_platform_recovery_blocks_app_cleanup():
    """Do not remove the exporter underneath an outstanding deployment."""
    run = CompatibilityRun(failure="post-upgrade")
    with pytest.raises(RuntimeError):
        run.run()
    run.failure = "recovery"
    with pytest.raises(Exception, match="recovery is incomplete"):
        run.teardown()
    assert "restore app" not in run.calls


def test_wrong_restored_build_fails_before_final_scrape():
    """The correct release prefix alone cannot establish app restoration."""
    run = CompatibilityRun(failure="wrong build")
    with pytest.raises(Exception, match="Validation Failed"):
        run.run()
    assert "post-rollback" not in run.calls


@pytest.mark.parametrize("target", [None, "invalid", "25.09", "26.03"])
def test_invalid_target_does_not_mutate(target):
    """Bad release pairs fail before preparation or state capture."""
    run = CompatibilityRun()
    with pytest.raises(Exception):
        run.run(target)
    run.state.capture.assert_not_called()
    run.preparation.prepare.assert_not_called()


@pytest.mark.parametrize("failure", ["node coverage", "host identity", "missing metric", "transport"])
def test_per_node_scrape_rejects_false_evidence(failure):
    """Use actual metric parsing and independent SSH identity checks."""
    exporter = NonCallableMock()
    exporter.wait_ready.return_value = {"controller-0": {"status": {"containerStatuses": []}}}
    helper = create_compatibility_keywords(exporter)
    node_exporter = NonCallableMock(spec=NodeInterfaceMetricsExporterKeywords)
    connection = NonCallableMock(spec=SSHConnection)
    connection.send.return_value = "other-node" if failure == "host identity" else "controller-0"
    node_exporter.interface_inventory.return_value = {"eth0": {"pciaddr": "", "vfs": {}}}
    node_exporter.read_endpoint.return_value = ExporterHttpOutput(200, 'network_interface_device_info{device="wrong"} 1')
    if failure == "transport":
        node_exporter.read_endpoint.side_effect = RuntimeError("connection refused")
    with patch(f"{KEYWORDS_MODULE}.NodeInterfaceMetricsExporterKeywords", return_value=node_exporter), patch(f"{KEYWORDS_MODULE}.LabConnectionKeywords") as connections, patch(f"{KEYWORDS_MODULE}.SystemHostListKeywords"), patch("framework.validation.validation.get_logger"):
        connections.return_value.get_ssh_for_hostname.return_value = connection
        connections.return_value.get_compute_ssh.return_value = connection
        with pytest.raises(Exception):
            helper.validate_metrics("post-upgrade", ("controller-0", "worker-0") if failure == "node coverage" else ("controller-0",))


def test_scrapes_each_node_again_in_each_phase():
    """Do not reuse metric output or host inventory across platform changes."""
    exporter = NonCallableMock()
    exporter.wait_ready.return_value = {node: {"status": {"containerStatuses": []}} for node in ("controller-0", "worker-0")}
    node_exporter = NonCallableMock(spec=NodeInterfaceMetricsExporterKeywords)
    connection = NonCallableMock(spec=SSHConnection)
    connection.get_return_code.return_value = 0
    connection.send.side_effect = ["controller-0", "worker-0"] * 3
    node_exporter.interface_inventory.return_value = {"eth0": {"pciaddr": "", "vfs": {"0": "0000:01:00.1"}}}
    node_exporter.read_endpoint.return_value = ExporterHttpOutput(200, 'network_interface_device_info{device="eth0"} 1\nnetwork_interface_vf_device_info{device="eth0",vf="0",pciaddr="0000:01:00.1"} 1')
    helper = create_compatibility_keywords(exporter)
    with patch(f"{KEYWORDS_MODULE}.NodeInterfaceMetricsExporterKeywords", return_value=node_exporter), patch(f"{KEYWORDS_MODULE}.LabConnectionKeywords") as connections, patch(f"{KEYWORDS_MODULE}.SystemHostListKeywords"), patch(f"{KEYWORDS_MODULE}.get_logger"), patch("framework.validation.validation.get_logger"):
        connections.return_value.get_ssh_for_hostname.return_value = connection
        connections.return_value.get_compute_ssh.return_value = connection
        nodes = helper.validate_metrics("pre")
        helper.validate_metrics("post-upgrade", nodes)
        helper.validate_metrics("post-rollback", nodes)
    assert node_exporter.read_endpoint.call_count == node_exporter.interface_inventory.call_count == 6


@pytest.mark.parametrize("application", [None, ("26.03-51", "applied")])
def test_baseline_archive_identity_is_checked(application):
    """Discover exactly one bundled archive or resolve the installed version."""
    exporter = NonCallableMock(spec=NodeInterfaceMetricsExporterKeywords)
    exporter.ssh_connection = NonCallableMock(spec=SSHConnection)
    exporter.ssh_connection.get_return_code.return_value = 0
    exporter.application_state.return_value = application
    archive = f"/apps/{APP}-26.03-51.tgz"
    exporter.ssh_connection.send.return_value = archive
    with patch(f"{KEYWORDS_MODULE}.ConfigurationManager") as configuration:
        configuration.get_app_config.return_value.get_base_application_path.return_value = "/apps"
        assert create_compatibility_keywords(exporter).get_baseline_package("26.03").get_artifact() == archive
    exporter.validate_artifact.assert_called_once_with(archive, "26.03-51")


@pytest.mark.parametrize("blocker", ["deployment", "alarm"])
def test_platform_blockers_stop_before_capture(blocker):
    """Do not change a lab with unrelated deployment or alarm failures."""
    run = CompatibilityRun()
    if blocker == "deployment":
        run.deployment = "deploy-host-failed"
    else:
        run.driver.require_no_blocking_alarms.side_effect = RuntimeError("blocking alarm")
    with pytest.raises(Exception):
        run.run()
    run.state.capture.assert_not_called()
    run.preparation.prepare.assert_not_called()
    assert not run.finalizers


@pytest.mark.parametrize("archives", ["", "/apps/a.tgz\n/apps/b.tgz", f"/apps/{APP}-25.09-38.tgz"])
def test_missing_ambiguous_or_wrong_release_archive_is_rejected(archives):
    """Never silently select a different baseline build or release."""
    exporter = NonCallableMock(spec=NodeInterfaceMetricsExporterKeywords)
    exporter.ssh_connection = NonCallableMock(spec=SSHConnection)
    exporter.ssh_connection.get_return_code.return_value = 0
    exporter.application_state.return_value = None
    exporter.ssh_connection.send.return_value = archives
    with patch(f"{KEYWORDS_MODULE}.ConfigurationManager") as configuration:
        configuration.get_app_config.return_value.get_base_application_path.return_value = "/apps"
        with pytest.raises(ValueError):
            create_compatibility_keywords(exporter).get_baseline_package("26.03")
    exporter.upload.assert_not_called()


API_UNAVAILABLE = 'Get "https://10.96.0.1:443/api/v1/pods?fieldSelector=spec.nodeName%3Dcontroller-0": dial tcp 10.96.0.1:443: connect: connection refused'
VALID_METRICS = 'network_interface_device_info{device="eth0"} 1'


def test_api_connectivity_convergence_is_retried():
    """Accept recovery only after a new successful, parseable scrape."""
    reader = Mock()
    reader.read_endpoint.side_effect = [ExporterHttpOutput(500, API_UNAVAILABLE), ExporterHttpOutput(200, VALID_METRICS)]
    helper = create_compatibility_keywords(Mock())
    with patch(f"{KEYWORDS_MODULE}.get_logger"), patch("framework.validation.validation.get_logger"), patch("framework.validation.validation.sleep"):
        metrics = helper._wait_for_metrics(reader, "post-upgrade", "controller-0")
    assert metrics.require_sample("network_interface_device_info", {"device": "eth0"}) == 1
    assert reader.read_endpoint.call_count == 2


@pytest.mark.parametrize("response", [ExporterHttpOutput(500, "internal server error"), ExporterHttpOutput(403, "forbidden"), ExporterHttpOutput(200, "malformed"), ExporterHttpOutput(200, "")])
def test_unrelated_errors_and_malformed_metrics_fail_immediately(response):
    """Do not retry functional or protocol errors as readiness convergence."""
    reader = Mock()
    reader.read_endpoint.return_value = response
    with patch("framework.validation.validation.get_logger"):
        with pytest.raises(ValueError):
            create_compatibility_keywords(Mock())._wait_for_metrics(reader, "post-upgrade", "controller-0")
    reader.read_endpoint.assert_called_once()


def test_persistent_api_connectivity_failure_times_out():
    """A permanently unavailable API must fail within the configured wait."""
    reader = Mock()
    reader.read_endpoint.return_value = ExporterHttpOutput(500, API_UNAVAILABLE)
    with patch(f"{KEYWORDS_MODULE}.get_logger"), patch("framework.validation.validation.get_logger"), patch("framework.validation.validation.time.time", side_effect=[0, 301]):
        with pytest.raises(TimeoutError):
            create_compatibility_keywords(Mock())._wait_for_metrics(reader, "post-upgrade", "controller-0")
    reader.read_endpoint.assert_called_once()


@pytest.mark.parametrize("line_output", [False, True])
def test_merged_exporter_api_reads_real_host_and_metrics(line_output: bool) -> None:
    """Exercise merged HTTP, sample and inventory APIs through the consumer.

    Args:
        line_output (bool): Use SSH's list-of-lines response representation.
    """
    connection = NonCallableMock(spec=SSHConnection)
    connection.get_return_code.return_value = 0
    outputs = [
        "controller-0",
        '[{"ifname":"eth0","flags":["UP"]}]',
        "/sys/devices/0000:01:00.0\nvirtfn0 /sys/devices/0000:01:00.1",
        'network_interface_device_info{device="eth0",pciaddr="0000:01:00.0"} 1\nnetwork_interface_vf_device_info{device="eth0",vf="0",pciaddr="0000:01:00.1"} 1\n200',
    ]
    connection.send.side_effect = [output.splitlines(keepends=True) if line_output else output for output in outputs]
    exporter = NonCallableMock()
    exporter.wait_ready.return_value = {"controller-0": {"status": {"containerStatuses": []}}}
    with patch(f"{KEYWORDS_MODULE}.LabConnectionKeywords") as connections, patch(f"{KEYWORDS_MODULE}.SystemHostListKeywords") as hosts, patch(f"{KEYWORDS_MODULE}.get_logger"), patch("keywords.base_keyword.get_logger"), patch("framework.validation.validation.get_logger"), patch.object(import_module(KEYWORDS_MODULE).ConfigurationManager, "get_k8s_config", return_value=Mock()):
        hosts.return_value.get_controllers.return_value = [Mock(get_host_name=lambda: "controller-0")]
        connections.return_value.get_ssh_for_hostname.return_value = connection
        assert create_compatibility_keywords(exporter).validate_metrics("post-upgrade", ("controller-0",)) == ("controller-0",)
    assert connection.send.call_count == 4


@pytest.mark.parametrize("return_code", [0, 1])
def test_baseline_discovery_checks_ssh_exit_and_archive_metadata(return_code: int) -> None:
    """Reject failed find commands and use the real merged artifact validator.

    Args:
        return_code (int): Find command exit status.
    """
    connection = NonCallableMock(spec=SSHConnection)
    connection.get_return_code.return_value = return_code
    connection.send.side_effect = [[f"/apps/{APP}-26.03-51.tgz\n"], ["metadata.yaml\n"], [f"app_name: {APP}\n", "app_version: 26.03-51\n"]]
    with patch("keywords.base_keyword.get_logger"), patch.object(import_module(KEYWORDS_MODULE).ConfigurationManager, "get_k8s_config", return_value=Mock()), patch.object(import_module(KEYWORDS_MODULE).ConfigurationManager, "get_app_config") as config:
        config.return_value.get_base_application_path.return_value = "/apps"
        exporter = NodeInterfaceMetricsExporterKeywords(connection)
        with patch.object(exporter, "application_state", return_value=None):
            if return_code:
                with pytest.raises(AssertionError):
                    create_compatibility_keywords(exporter).get_baseline_package("26.03")
                assert connection.send.call_count == 1
            else:
                assert create_compatibility_keywords(exporter).get_baseline_package("26.03").get_artifact() == f"/apps/{APP}-26.03-51.tgz"
                assert connection.send.call_count == 3


@pytest.mark.parametrize("clears", [True, False])
def test_rollback_waits_for_alarm_clearance(clears):
    """Allow delayed alarm clearance but keep persistent alarms fatal."""
    run = CompatibilityRun()
    run.health.get_app_or_deploy_alarm_count.side_effect = [0, 1, 0] if clears else [0, 1, 1]
    with patch("framework.validation.validation.get_logger"), patch("framework.validation.validation.sleep"), patch("framework.validation.validation.time.time", side_effect=[0, 1, 301]):
        if clears:
            run.run()
            assert "post-rollback" in run.calls
        else:
            with pytest.raises(TimeoutError):
                run.run()
            assert "post-rollback" not in run.calls
    assert run.health.get_app_or_deploy_alarm_count.call_count == 3
