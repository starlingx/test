"""Stateful recovery tests covering partial mutation and independent cleanup."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from keywords.cloud_platform.applications.node_interface_metrics_exporter_state import NodeInterfaceMetricsExporterState


class FakeExporter:
    """Model application operations with mutations that can precede failure."""

    def __init__(self, application=None):
        """Initialize the application model."""
        self.application = application
        self.values = {"image": {"tag": "original"}} if application else {}
        self.labels = {"worker-0": None}
        self.fail_apply = False

    def application_state(self):
        """Read current version/status."""
        return self.application

    def validate_artifact(self, artifact, version):
        """Reject missing recovery inputs before mutation."""
        if not artifact or not version:
            raise ValueError("missing artifact")

    def user_overrides(self):
        """Return a detached original override mapping."""
        return deepcopy(self.values)

    def exporter_labels(self):
        """Return a detached label mapping."""
        return dict(self.labels)

    def discover_pods(self):
        """Return no orphan pods in the supported baseline."""
        return []

    def wait_absent(self):
        """Require a removed runtime."""
        assert self.application is None or self.application[1] == "uploaded"

    def chart_enabled(self):
        """Return supported chart enablement."""
        return True

    def set_chart_enabled(self, enabled):
        """Restore supported chart enablement."""
        assert enabled

    def wait_ready(self):
        """Require an applied app."""
        assert self.application[1] == "applied"
        return {"worker-0": {"status": {"containerStatuses": [{"name": "exporter", "imageID": "original-digest"}]}}}

    def upload(self, artifact, version):
        """Upload the supplied version."""
        self.application = (version, "uploaded")

    def apply(self):
        """Apply may fail after modifying application and labels."""
        self.labels["worker-0"] = "true"
        self.application = (self.application[0], "apply-failed" if self.fail_apply else "applied")
        if self.fail_apply:
            raise RuntimeError("partial apply")

    def remove(self):
        """Remove runtime application resources."""
        self.application = (self.application[0], "uploaded")

    def delete(self):
        """Delete the uploaded application."""
        self.application = None
        self.values = {}

    def set_overrides(self, values):
        """Restore an exact override mapping."""
        self.values = deepcopy(values)

    def restore_labels(self, values):
        """Restore exporter labels."""
        self.labels = dict(values)

    def verify_candidate(self, version, images):
        """Check candidate version in the model."""
        assert self.application == (version, "applied")
        return self.wait_ready()


def test_partial_setup_cleanup_registered_first():
    """An apply failure after mutation still restores absence and original labels."""
    exporter_keywords = FakeExporter()
    state = NodeInterfaceMetricsExporterState(exporter_keywords)
    finalizers = []
    state.capture(finalizers.append)
    exporter_keywords.fail_apply = True
    with pytest.raises(RuntimeError), patch("keywords.cloud_platform.applications.node_interface_metrics_exporter_state.get_logger"):
        state.prepare("/candidate.tgz", "1", {"exporter": "sha256:" + "a" * 64}, {"application_revision": "app-sha", "automation_revision": "test-sha", "build_reference": "local-build"})
    finalizers[0]()
    assert exporter_keywords.application is None
    assert exporter_keywords.labels == {"worker-0": None}


@pytest.mark.parametrize("status", ["applied", "uploaded"])
def test_restore_existing_version_overrides_labels(status):
    """Consumer changes do not discard a pre-existing application baseline."""
    exporter_keywords = FakeExporter(("original", status))
    state = NodeInterfaceMetricsExporterState(exporter_keywords)
    state.capture(lambda callback: None, "/original.tgz")
    exporter_keywords.application = ("candidate", "applied")
    exporter_keywords.values = {"image": {"tag": "candidate"}}
    exporter_keywords.labels["worker-0"] = "true"
    state.restore()
    assert exporter_keywords.application == ("original", status)
    assert exporter_keywords.values == {"image": {"tag": "original"}}
    assert exporter_keywords.labels == {"worker-0": None}
    state.restore()


def test_cleanup_failure_does_not_skip_application_recovery():
    """All independent stages run and cleanup errors remain visible."""
    exporter_keywords = FakeExporter()
    state = NodeInterfaceMetricsExporterState(exporter_keywords)
    state.capture(lambda callback: None)
    order = []
    state.add_cleanup("first", lambda: order.append("first"))

    def fail():
        """Model failed consumer resource cleanup."""
        order.append("second")
        raise RuntimeError("workload could not be deleted")

    state.add_cleanup("second", fail)
    exporter_keywords.application = ("candidate", "applied")
    with pytest.raises(ExceptionGroup, match="recovery failed"):
        state.restore()
    assert exporter_keywords.application is None
    assert order == ["second", "first"]
    assert not state.baseline_restored


def test_unsupported_baseline_before_mutation():
    """A transitioning baseline cannot be treated as restorable."""
    exporter_keywords = FakeExporter(("original", "applying"))
    state = NodeInterfaceMetricsExporterState(exporter_keywords)
    with pytest.raises(ValueError):
        state.capture(lambda callback: None, "/original.tgz")
    assert not state.baseline_captured
    assert exporter_keywords.application == ("original", "applying")


def test_missing_provenance_prevents_setup():
    """Unknown application/build provenance cannot produce a candidate result."""
    exporter_keywords = FakeExporter()
    state = NodeInterfaceMetricsExporterState(exporter_keywords)
    state.capture(lambda callback: None)
    with pytest.raises(ValueError, match="Record application revision"):
        state.prepare("/candidate.tgz", "1", {"exporter": "sha256:" + "a" * 64}, {})
    assert exporter_keywords.application is None


def test_prepare_requires_registered_recovery():
    """Consumers cannot mutate an app before recovery registration."""
    exporter_keywords = FakeExporter()
    state = NodeInterfaceMetricsExporterState(exporter_keywords)
    with pytest.raises(RuntimeError):
        state.prepare("/candidate.tgz", "1", {}, {})
    assert exporter_keywords.application is None


def test_successful_candidate_records_provenance():
    """Application source and automation source remain separate in evidence."""
    exporter_keywords = FakeExporter()
    state = NodeInterfaceMetricsExporterState(exporter_keywords)
    state.capture(lambda callback: None)
    provenance = {"application_revision": "unmerged-app-sha", "automation_revision": "test-sha", "build_reference": "local-build"}
    with patch("keywords.cloud_platform.applications.node_interface_metrics_exporter_state.get_logger"):
        state.prepare("/candidate.tgz", "candidate", {"exporter": "sha256:" + "a" * 64}, provenance)
    assert state.candidate_evidence["provenance"] == provenance
    state.restore()
    assert exporter_keywords.application is None
