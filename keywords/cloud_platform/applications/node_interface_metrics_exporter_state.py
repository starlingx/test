"""Registered, recoverable exporter state for independent ACE consumers."""

import json
import re
from collections.abc import Callable
from copy import deepcopy

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.applications.node_interface_metrics_exporter_keywords import NodeInterfaceMetricsExporterKeywords


class NodeInterfaceMetricsExporterState:
    """Restore supported absent, uploaded and applied application baselines.

    Consumers register workload/override/chart recovery before each mutation.
    Unsupported transitional baselines are rejected before registering setup.
    """

    def __init__(self, keywords: NodeInterfaceMetricsExporterKeywords):
        """Initialize recovery tracking without modifying the lab.

        Args:
            keywords (NodeInterfaceMetricsExporterKeywords): Existing controller keyword instance.
        """
        self.keywords = keywords
        self.baseline_captured = False
        self.baseline_restored = False
        self.cleanup_actions = []
        self.baseline_application_state = None
        self.baseline_user_overrides = {}

        self.baseline_node_labels = {}
        self.baseline_artifact_path = None
        self.baseline_chart_enabled = True
        self.baseline_image_ids_by_node = {}
        self.candidate_evidence = None

    def capture(self, addfinalizer: Callable, baseline_artifact: str | None = None) -> None:
        """Capture a recoverable baseline and register restoration before setup.

        Args:
            addfinalizer (Callable): The consuming pytest request.addfinalizer method.
            baseline_artifact (str | None): Exact original-version archive when an app exists.
        """
        if self.baseline_captured:
            raise RuntimeError("Exporter baseline already captured")
        # Validate the original state before registering any mutation.
        exporter_keywords = self.keywords
        application = exporter_keywords.application_state()
        overrides = {}
        if application:
            if application[1] not in ("uploaded", "applied"):
                raise ValueError(f"Unsupported exporter baseline state: {application}")
            exporter_keywords.validate_artifact(baseline_artifact, application[0])
            self.baseline_chart_enabled = exporter_keywords.chart_enabled()
            if not self.baseline_chart_enabled:
                raise ValueError("Disabled chart baselines are unsupported; reconcile before testing")
            overrides = exporter_keywords.user_overrides()
            if any(key in overrides for key in ("name", "namespace", "labels")):
                raise ValueError("Baseline identity overrides are unsupported; reconcile before testing")

            # Capture the running image identities only for active workloads.
            if application[1] == "applied":
                self.baseline_image_ids_by_node = self._image_snapshot()
        if (application is None or application[1] == "uploaded") and exporter_keywords.discover_pods():
            raise ValueError("Exporter pods exist without an applied baseline; reconcile before testing")

        # Save the complete baseline and register recovery after read-only checks.
        self.baseline_node_labels = exporter_keywords.exporter_labels()
        self.baseline_application_state, self.baseline_user_overrides, self.baseline_artifact_path = application, deepcopy(overrides), baseline_artifact
        addfinalizer(self.restore)
        self.baseline_captured = True

    def add_cleanup(self, description: str, callback: Callable[[], None]) -> None:
        """Register idempotent consumer cleanup before changing a resource.

        Args:
            description (str): Resource/action identity for teardown diagnostics.
            callback (Callable[[], None]): Restore only the consumer's owned changes.
        """
        if not self.baseline_captured or self.baseline_restored:
            raise RuntimeError("Capture an active exporter baseline first")
        self.cleanup_actions.append((description, callback))

    def prepare(self, artifact: str, version: str, images: dict[str, str], provenance: dict[str, str]) -> dict[str, dict]:
        """Install or verify an explicit candidate with recovery already registered.

        Existing different versions are rejected; explicit app-update consumers
        perform their update after capture using the existing application API.

        Args:
            artifact (str): Staged candidate archive, including unmerged builds.
            version (str): Expected candidate application version.
            images (dict[str, str]): Expected immutable digests by container name.
            provenance (dict[str, str]): application_revision, automation_revision and build_reference.

        Returns:
            dict[str, dict]: Candidate identity evidence for each ready node.
        """
        if not self.baseline_captured or self.baseline_restored:
            raise RuntimeError("Register exporter recovery before preparing a candidate")

        # Validate candidate identity and provenance before installation.
        required_provenance_fields = {"application_revision", "automation_revision", "build_reference"}
        if not required_provenance_fields <= provenance.keys() or any(not isinstance(provenance[key], str) or not provenance[key].strip() for key in required_provenance_fields):
            raise ValueError("Record application revision, automation revision and candidate build separately")
        get_logger().log_info(f"Exporter candidate provenance: {json.dumps(provenance, sort_keys=True)}")
        exporter_keywords = self.keywords
        exporter_keywords.validate_artifact(artifact, version)
        if not images or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) for digest in images.values()):
            raise ValueError("Provide expected candidate image digests before mutation")

        # Reuse a matching installation; app updates have a separate consumer.
        current_application_state = exporter_keywords.application_state()
        if current_application_state and current_application_state[0] != version:
            raise ValueError("Use the explicit application-update consumer for a different installed version")
        if current_application_state is None:
            exporter_keywords.upload(artifact, version)
        if current_application_state is None or current_application_state[1] != "applied":
            exporter_keywords.apply()

        # Record the identity actually running after apply.
        pods = exporter_keywords.verify_candidate(version, images)
        self.candidate_evidence = {"provenance": dict(provenance), "artifact": artifact, "version": version, "images": dict(images), "pods": pods}
        return pods

    def _restore_application(self) -> None:
        """Reconcile application version/status and exact stored overrides."""
        exporter_keywords = self.keywords
        current_application_state = exporter_keywords.application_state()
        baseline_application_state = self.baseline_application_state
        if current_application_state == baseline_application_state and (baseline_application_state is None or (baseline_application_state[1] == "uploaded" and exporter_keywords.user_overrides() == self.baseline_user_overrides and exporter_keywords.chart_enabled() == self.baseline_chart_enabled)):
            return
        if current_application_state and current_application_state[1] not in ("uploaded", "applied", "apply-failed", "remove-failed", "upload-failed"):
            raise ValueError(f"Exporter recovery requires a settled application: {current_application_state}")

        # Remove incompatible or failed state before restoring the original app.
        requires_application_replacement = current_application_state and (baseline_application_state is None or current_application_state[0] != baseline_application_state[0] or current_application_state[1] == "upload-failed")
        if current_application_state and (requires_application_replacement or current_application_state[1] in ("apply-failed", "remove-failed") or (baseline_application_state and baseline_application_state[1] == "uploaded")):
            if current_application_state[1] not in ("uploaded", "upload-failed"):
                exporter_keywords.remove()
            if requires_application_replacement:
                exporter_keywords.delete()
                current_application_state = None

        # Restore the original chart settings before reapplying.
        if baseline_application_state:
            if current_application_state is None:
                exporter_keywords.upload(self.baseline_artifact_path, baseline_application_state[0])
            exporter_keywords.set_chart_enabled(self.baseline_chart_enabled)
            exporter_keywords.set_overrides(self.baseline_user_overrides)
            if baseline_application_state[1] == "applied":
                exporter_keywords.apply()
        if exporter_keywords.application_state() != baseline_application_state:
            raise ValueError("Exporter baseline version/status was not restored")

    def restore(self) -> None:
        """Attempt independent cleanup stages and retain failures for retry."""
        if not self.baseline_captured or self.baseline_restored:
            return
        recovery_errors = []
        recovery_stages = list(reversed(self.cleanup_actions)) + [("application", self._restore_application), ("node labels", lambda: self.keywords.restore_labels(self.baseline_node_labels)), ("verification", self._verify)]
        for description, action in recovery_stages:
            try:
                action()
            except Exception as error:
                recovery_errors.append(RuntimeError(f"Exporter recovery {description}: {error}"))
        if recovery_errors:
            raise ExceptionGroup("Exporter baseline recovery failed", recovery_errors)
        self.baseline_restored = True

    def _verify(self) -> None:
        """Verify final identity, overrides, labels and applied readiness."""
        exporter_keywords = self.keywords
        if exporter_keywords.application_state() != self.baseline_application_state or exporter_keywords.exporter_labels() != self.baseline_node_labels:
            raise ValueError("Exporter baseline state differs after recovery")
        if self.baseline_application_state:
            if exporter_keywords.chart_enabled() != self.baseline_chart_enabled or exporter_keywords.user_overrides() != self.baseline_user_overrides:
                raise ValueError("Exporter baseline overrides differ after recovery")
            if self.baseline_application_state[1] == "applied" and self._image_snapshot() != self.baseline_image_ids_by_node:
                raise ValueError("Exporter baseline running image identities were not restored")
        if self.baseline_application_state is None or self.baseline_application_state[1] == "uploaded":
            exporter_keywords.wait_absent()

    def _image_snapshot(self) -> dict[str, dict[str, str]]:
        """Read ready running image identities for exact baseline verification.

        Returns:
            dict[str, dict[str, str]]: Node/container image identities.
        """
        pods = self.keywords.wait_ready()
        images = {node: {item["name"]: item.get("imageID", "") for item in pod["status"]["containerStatuses"]} for node, pod in pods.items()}
        if not images or any(not containers or not all(containers.values()) for containers in images.values()):
            raise ValueError("Missing baseline running image identities")
        return images
