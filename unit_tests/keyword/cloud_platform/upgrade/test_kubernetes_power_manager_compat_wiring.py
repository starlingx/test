"""Wiring contracts for the kubernetes-power-manager upgrade/rollback compatibility test.

These tests drive the real test body with stateful stand-ins for the platform, the application
health reads and the KPM keyword, so they exercise the wiring without a lab or SSH:

  - the install-if-missing step runs for every baseline (absent / uploaded-not-applied / applied)
    and only uploads when the app is actually absent,
  - the phases run in order (baseline -> upgrade -> rollback), each asserting the version against
    the release the platform reports and reconciling the power-node-agent,
  - the starting release is restored on teardown.
"""

from contextlib import ExitStack
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

import pytest

MODULE = "testcases.cloud_platform.upgrade.app_compat.test_kubernetes_power_manager_upgrade_compat"


class CompatibilityModel:
    """Drive the real test with a stateful platform, health and KPM collaborators."""

    def __init__(self, release="from-release", baseline="applied", target="to-release", node_count=2, nfd_present=True, label_already_present=False):
        self.original_release = release
        self.release = release
        self.target = target
        self.node_count = node_count
        # baseline is one of: "applied", "uploaded" (present, not applied), "absent".
        self.baseline = baseline
        self.applied = baseline == "applied"
        self.present = baseline in ("applied", "uploaded")
        self.nfd_present = nfd_present
        self.label_already_present = label_already_present
        self.app_version_value = f"{release}-10"
        self.calls = []
        self.ensure_calls = []
        self.agent_ready_calls = []
        self.finalizers = []
        self.uploaded_apps = []
        self.label_assigned = False

        self.deploy = SimpleNamespace(get_running_release=lambda: self.release, deploy_upgrade=self.deploy_upgrade, deploy_rollback=self.deploy_rollback)
        self.health = SimpleNamespace(
            wait_for_app_applied=lambda app: self.calls.append(f"applied:{app}"),
            get_app_version=lambda app: self.app_version_value,
            get_unhealthy_pod_count=lambda ns: 0,
            get_app_or_deploy_alarm_count=lambda: 0,
        )
        self.kpm = SimpleNamespace(
            ensure_applied=self.ensure_applied,
            ensure_power_management_label=self.ensure_label,
            wait_for_power_node_agent_ready=self.agent_ready,
            remove_power_management_label=self.remove_power_management_label,
            remove_app=self.remove_app,
        )
        self.recovery = SimpleNamespace(restore_to_release=self.restore_release)
        names = {"kubernetes-power-manager": "kubernetes-power-manager", "node-feature-discovery": "node-feature-discovery"}
        namespaces = {"kubernetes-power-manager": "intel-power", "node-feature-discovery": "node-feature-discovery"}
        self.config = SimpleNamespace(
            get_app_name=lambda key: names[key],
            get_namespace=lambda key: namespaces[key],
            get_to_version=lambda: self.target,
        )
        self.app_config = SimpleNamespace(get_base_application_path=lambda: "/usr/local/share/applications/helm/")
        hosts = [SimpleNamespace() for _ in range(self.node_count)]
        self.host_output = SimpleNamespace(get_hosts=lambda: hosts)
        self.request = SimpleNamespace(addfinalizer=self.finalizers.append)

    def ensure_applied(self, app_name, tar_file_path):
        """Model the idempotent install-if-missing step for NFD (dependency) and KPM.

        Returns True when this call uploaded the app (it was absent), mirroring the production
        keyword, so the test can register cleanup only for what it installed.
        """
        assert app_name in ("kubernetes-power-manager", "node-feature-discovery")
        assert tar_file_path == f"/usr/local/share/applications/helm/{app_name}*.tgz"
        self.ensure_calls.append(app_name)
        if app_name == "node-feature-discovery":
            uploaded = app_name not in self.uploaded_apps and not self.nfd_present
            if uploaded:
                self.uploaded_apps.append(app_name)
            return uploaded
        # kubernetes-power-manager
        self.calls.append("ensure_applied")
        uploaded = False
        if not self.applied:
            if not self.present:
                self.uploaded_apps.append(app_name)
                uploaded = True
            self.applied = True
            self.present = True
            self.app_version_value = f"{self.original_release}-10"
        return uploaded

    def agent_ready(self, namespace, expected_nodes):
        """Record each per-node agent reconciliation check and its ordering marker.

        Wired directly as the KPM stand-in in __init__ so there is a single agent-check
        implementation. The 'agent' marker drives deploy_upgrade's ordering assert, and the label
        must have been assigned before the first agent check runs.
        """
        assert self.label_assigned, "power-management label must be assigned before the agent check"
        assert namespace == "intel-power" and expected_nodes == self.node_count
        self.agent_ready_calls.append(self.release)
        self.calls.append("agent")

    def ensure_label(self, app_name):
        """Model assigning the label where missing and reapplying only when it changed.

        Returns the hosts newly labelled (empty when all hosts already carried it), mirroring the
        production keyword. The reapply ordering marker is only recorded when a label was actually
        assigned, so the wiring test can assert the reapply is conditional.
        """
        assert app_name == "kubernetes-power-manager"
        self.calls.append("ensure_label")
        self.label_assigned = True
        if self.label_already_present:
            return []
        self.calls.append(f"reapply:{app_name}")
        return [f"host-{i}" for i in range(self.node_count)]

    def remove_power_management_label(self, host_names):
        """Model teardown removal of the label from the hosts the test labelled."""
        self.calls.append(f"remove_label:{list(host_names)}")

    def remove_app(self, app_name):
        """Model teardown removal of an app the test uploaded."""
        self.calls.append(f"remove_app:{app_name}")

    def deploy_upgrade(self, version, leave_at_activate_done):
        """Upgrade must run after the baseline check and leave the deploy rollback-able."""
        assert version == self.target and leave_at_activate_done
        assert self.calls[-1] == "agent" and self.applied
        self.calls.append("upgrade")
        self.release = version
        self.app_version_value = f"{version}-71"

    def deploy_rollback(self):
        """Rollback returns the platform and app to the starting release."""
        self.calls.append("rollback")
        self.release = self.original_release
        self.app_version_value = f"{self.original_release}-10"

    def restore_release(self, release):
        """Best-effort platform recovery on teardown."""
        assert release == self.original_release
        self.calls.append("restore release")

    def run(self):
        """Execute the production body without lab configuration or SSH."""
        module = import_module(MODULE)
        with ExitStack() as stack:
            for name, value in {
                "SoftwareDeploySequenceKeywords": self.deploy,
                "ApplicationHealthKeywords": self.health,
                "KubernetesPowerManagerCompatCheckKeywords": self.kpm,
                "UpgradeRecoveryKeywords": self.recovery,
                "SystemHostListKeywords": SimpleNamespace(get_system_host_list=lambda: self.host_output),
            }.items():
                stack.enter_context(patch.object(module, name, return_value=value))
            stack.enter_context(patch.object(module, "LabConnectionKeywords"))
            stack.enter_context(patch.object(module, "get_logger"))
            stack.enter_context(patch("framework.validation.validation.get_logger"))
            stack.enter_context(patch.object(module.ConfigurationManager, "get_app_upgrade_compat_config", return_value=self.config))
            stack.enter_context(patch.object(module.ConfigurationManager, "get_app_config", return_value=self.app_config))
            module.test_kubernetes_power_manager_upgrade_rollback(self.request)

    def teardown(self):
        """Run pytest's reverse finalizer order."""
        for finalizer in reversed(self.finalizers):
            finalizer()


@pytest.mark.parametrize("release", ["n-minus-one", "n-minus-two"])
@pytest.mark.parametrize("baseline", ["absent", "uploaded", "applied"])
def test_install_if_missing_then_phases_in_order(release: str, baseline: str) -> None:
    """Ensure NFD first, install KPM when needed, then run baseline/upgrade/rollback in order.

    Args:
        release (str): A stand-in for the installed starting release (the test is release-agnostic;
            the starting release is read from the platform at runtime, so only its identity as a
            value that flows through the phases matters here).
        baseline (str): KPM state before the test: absent, uploaded-not-applied, or applied.
    """
    model = CompatibilityModel(release=release, baseline=baseline)
    model.run()

    # NFD (the dependency) is ensured before KPM, then the KPM install-if-missing step runs.
    assert model.ensure_calls == ["node-feature-discovery", "kubernetes-power-manager"]
    assert "ensure_applied" in model.calls
    # The power-management label is assigned before the first agent reconciliation check, and the
    # app is reapplied (to settle the label config change) between the two.
    assert model.calls.index("ensure_label") < model.calls.index("reapply:kubernetes-power-manager") < model.calls.index("agent")
    assert [c for c in model.calls if c in ("upgrade", "rollback")] == ["upgrade", "rollback"]
    # The agent is reconciled three times: baseline, post-upgrade, post-rollback.
    assert model.agent_ready_calls == [model.original_release, model.target, model.original_release]
    # The KPM tarball is uploaded only when the app was genuinely absent.
    assert ("kubernetes-power-manager" in model.uploaded_apps) == (baseline == "absent")
    # NFD (the agent's dependency) is re-verified as applied in every phase, not just at install:
    # baseline, post-upgrade and post-rollback.
    assert model.calls.count("applied:node-feature-discovery") == 3

    model.teardown()
    assert model.calls[-1] == "restore release"


def test_teardown_removes_only_what_the_test_installed() -> None:
    """On a from-scratch lab the finalizer removes the label and both apps it installed."""
    model = CompatibilityModel(baseline="absent", nfd_present=False)
    model.run()
    model.teardown()
    # The label was newly assigned and both apps were uploaded, so all three are cleaned up,
    # label first then KPM then NFD (reverse of install), before the release restore.
    assert any(c.startswith("remove_label:") for c in model.calls)
    assert "remove_app:kubernetes-power-manager" in model.calls
    assert "remove_app:node-feature-discovery" in model.calls
    remove_label_call = next(c for c in model.calls if c.startswith("remove_label:"))
    assert model.calls.index(remove_label_call) < model.calls.index("remove_app:kubernetes-power-manager") < model.calls.index("remove_app:node-feature-discovery")


def test_teardown_leaves_preexisting_apps_in_place() -> None:
    """When KPM/NFD were already applied and labelled, teardown removes nothing it did not add."""
    model = CompatibilityModel(baseline="applied", nfd_present=True, label_already_present=True)
    model.run()
    model.teardown()
    assert not any(c.startswith("remove_app:") for c in model.calls)
    # No hosts were newly labelled, so the label-removal call is for an empty host list (no-op).
    assert "remove_label:[]" in model.calls


def test_reapply_is_skipped_when_label_already_present() -> None:
    """A rerun where every host already carries the label does not reapply the app."""
    model = CompatibilityModel(baseline="applied", label_already_present=True)
    model.run()
    assert "ensure_label" in model.calls
    assert not any(c.startswith("reapply:") for c in model.calls)


def test_nfd_dependency_is_ensured_before_kpm() -> None:
    """NFD is uploaded if absent and always ensured before KPM."""
    model = CompatibilityModel(baseline="absent", nfd_present=False)
    model.run()
    assert model.ensure_calls == ["node-feature-discovery", "kubernetes-power-manager"]
    assert "node-feature-discovery" in model.uploaded_apps


@pytest.mark.parametrize("node_count", [1, 2])
def test_node_count_is_passed_to_agent_check(node_count: int) -> None:
    """The expected agent count is the number of hosts the platform reports, for any node count."""
    model = CompatibilityModel(node_count=node_count)
    model.run()
    # agent_ready asserts expected_nodes == node_count on every call, so reaching here already
    # proves the count was threaded through; make the count itself explicit in the test too.
    assert model.node_count == node_count
    assert model.agent_ready_calls == [model.original_release, model.target, model.original_release]


def test_starting_release_is_restored_on_teardown() -> None:
    """A finalizer restoring the starting release is always registered."""
    model = CompatibilityModel()
    model.run()
    assert "restore release" not in model.calls
    model.teardown()
    assert model.calls[-1] == "restore release"
