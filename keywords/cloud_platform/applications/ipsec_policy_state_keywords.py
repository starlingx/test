"""Owned policy resources with recovery registered before any mutation."""

import copy
import json
import re
from collections.abc import Callable
from shlex import quote
from uuid import uuid4

import yaml

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.applications.ipsec_policy_keywords import APPLICATION_NAME, POLICY_RESOURCE, IPsecPolicyKeywords
from keywords.cloud_platform.applications.object.ipsec_policy_images_output import IPsecPolicyImagesOutput
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_update_input import SystemApplicationUpdateInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_update_keywords import SystemApplicationUpdateKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.get_resource.object.kubernetes_resource_list_output import KubernetesResourceListOutput
from keywords.k8s.get_resource.object.kubernetes_resource_object import KubernetesResourceObject
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.python.string import String

OWNER_LABEL = "starlingx.io/ace-ipsec-run"
TERMINAL_APPLICATION_STATUSES = ["uploaded", "applied", "upload-failed", "apply-failed", "remove-failed", "update-failed"]
CHART_NAMES = ("ipsec-policy-agent", "ipsec-policy-manager")


class IPsecPolicyStateKeywords(K8sBaseKeyword):
    """Capture baseline and manage resources owned by one test execution.

    Existing policies are read-only. Whole-app mutation and deletion of the last
    policy require an explicitly exclusive disposable lab.
    """

    def __init__(self, ssh_connection: SSHConnection, kubeconfig_path: str | None = None):
        """Initialize an isolated run identity.

        Args:
            ssh_connection (SSHConnection): Controller connection.
            kubeconfig_path (str | None): Optional kubeconfig path.
        """
        super().__init__(ssh_connection, kubeconfig_path)
        self.policy_keywords = IPsecPolicyKeywords(ssh_connection, kubeconfig_path)
        self.run_id = f"ace-ipsec-{uuid4().hex[:16]}"
        self.captured = False
        self.resources = []
        self.files = []
        self.cleanups = []
        self.exclusive = False
        self.original_application = None
        self.application_prepared = False
        self.application = None
        self.policies = None
        self.charts = {}
        self.labels = {}
        self.candidate_package_version = None

    def get_run_id(self) -> str:
        """Return the identity shared by this run's owned resources.

        Returns:
            str: Unique run identifier.
        """
        return self.run_id

    def prepare_application(self, addfinalizer: Callable, artifact: str, version: str, exclusive: bool = False) -> None:
        """Prepare an absent or uploaded application with outer recovery.

        Call before capture_state. Pytest then cleans owned policy resources
        before restoring the application's original absent/uploaded state.

        Args:
            addfinalizer (Callable): Pytest finalizer registration function.
            artifact (str): Exact staged controller-local application archive.
            version (str): Expected package version.
            exclusive (bool): Explicit exclusive disposable-lab assignment.
        """
        if self.captured or self.application_prepared:
            raise KeywordException("Prepare the application once, before fixture capture")
        original = SystemApplicationListKeywords(self.ssh_connection).get_application_state(APPLICATION_NAME)
        if original == (version, "applied"):
            return
        if not exclusive or (original is not None and original != (version, "uploaded")):
            raise KeywordException("Preparation supports absent or matching uploaded applications on an exclusive lab")
        self.validate_application_archive(artifact, version)
        self.original_application = original
        self.application_prepared = True
        # Register before upload/apply, including mutations with lost replies.
        addfinalizer(self.restore_application)
        if original is None:
            request = SystemApplicationUploadInput()
            request.set_app_name(APPLICATION_NAME)
            request.set_tar_file_path(quote(artifact))
            SystemApplicationUploadKeywords(self.ssh_connection).system_application_upload(request)
        SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply(APPLICATION_NAME)
        if SystemApplicationListKeywords(self.ssh_connection).get_application_state(APPLICATION_NAME) != (version, "applied"):
            raise KeywordException("Prepared application identity differs from requested candidate")

    def validate_application_archive(self, artifact: str, version: str) -> None:
        """Validate the exact staged application archive before a mutation.

        Args:
            artifact (str): Absolute controller-local archive path.
            version (str): Expected application version.
        """
        if not version or not artifact.startswith("/") or any(character in artifact for character in "*?[]\n\r"):
            raise KeywordException("An exact staged archive and expected version are required")
        output = self.ssh_connection.send(f"tar -tf {quote(artifact)}")
        self.validate_success_return_code(self.ssh_connection)
        text = String.normalize_command_output(output)
        members = [member for member in text.splitlines() if member in ("metadata.yaml", "./metadata.yaml")]
        if len(members) != 1:
            raise KeywordException("Archive requires one root metadata.yaml")
        output = self.ssh_connection.send(f"tar -xOf {quote(artifact)} {quote(members[0])}")
        self.validate_success_return_code(self.ssh_connection)
        metadata = yaml.safe_load(String.normalize_command_output(output))
        if not isinstance(metadata, dict) or metadata.get("app_name") != APPLICATION_NAME or str(metadata.get("app_version")) != version:
            raise KeywordException("Archive does not match the requested application/version")

    def update_candidate_package(self, artifact: str, version: str, baseline_artifact: str) -> None:
        """Update a captured applied baseline and register package restoration.

        Both archives must be retained on the controller throughout the run.
        Use a distinct candidate package version, including metadata-only builds.
        The platform update API enforces its supported update/downgrade contract;
        this fixture never deletes shared CRDs to force an unsupported transition.

        Args:
            artifact (str): Exact staged candidate archive.
            version (str): Candidate package version distinct from the baseline.
            baseline_artifact (str): Exact original package for reverse update.
        """
        if not self.captured or not self.exclusive:
            raise KeywordException("Package updates require a captured exclusive lab")
        if self.candidate_package_version is not None or version == self.application[0]:
            raise KeywordException("Use one distinct candidate package version per captured fixture")
        self.validate_application_archive(artifact, version)
        self.validate_application_archive(baseline_artifact, self.application[0])
        baseline_images = self.policy_keywords.get_running_images()

        def restore_package() -> None:
            """Restore the original package before checking its effective images."""
            applications = SystemApplicationListKeywords(self.ssh_connection)
            applications.validate_app_status_in_list(APPLICATION_NAME, TERMINAL_APPLICATION_STATUSES, timeout=300, polling_sleep_time=5)
            current = applications.get_application_state(APPLICATION_NAME)
            if current != self.application:
                self._update_application_archive(baseline_artifact, self.application[0])
            failures = []
            for chart, baseline in self.charts.items():
                try:
                    self._set_chart_overrides(chart, baseline["user_overrides"])
                except Exception as error:
                    failures.append(f"{chart}: {error}")
            if failures:
                raise KeywordException("Package baseline overrides could not be restored: " + "; ".join(failures))
            self._reapply_baseline(baseline_images)

        self.add_cleanup("Restore original application package", restore_package)
        self.candidate_package_version = version
        self._update_application_archive(artifact, version)

    def _update_application_archive(self, artifact: str, version: str) -> None:
        """Execute the shared application update API and verify its outcome.

        Args:
            artifact (str): Previously validated archive path.
            version (str): Expected applied version.
        """
        request = SystemApplicationUpdateInput()
        request.set_app_name(APPLICATION_NAME)
        request.set_tar_file_path(quote(artifact))
        request.set_timeout_in_seconds(600)
        SystemApplicationUpdateKeywords(self.ssh_connection).system_application_update(request)
        if SystemApplicationListKeywords(self.ssh_connection).get_application_state(APPLICATION_NAME) != (version, "applied"):
            raise KeywordException("Updated application differs from the requested package")

    def restore_application(self) -> None:
        """Restore the original inactive state without removing foreign policies."""
        applications = SystemApplicationListKeywords(self.ssh_connection)
        current = applications.get_application_state(APPLICATION_NAME)
        if current and current[1] in ("uploading", "applying", "updating", "removing"):
            applications.validate_app_status_in_list(APPLICATION_NAME, TERMINAL_APPLICATION_STATUSES, timeout=300, polling_sleep_time=5)
            current = applications.get_application_state(APPLICATION_NAME)
        if current == self.original_application:
            return
        if current is None:
            raise KeywordException("Originally uploaded application disappeared during validation")
        if current[1] in ("applied", "apply-failed", "remove-failed"):
            policies = self.policy_keywords.get_policies().get_policies() if self.policy_keywords.has_policy_crd() else []
            if policies:
                raise KeywordException("Policies remain; refusing whole-application removal")
            request = SystemApplicationRemoveInput()
            request.set_app_name(APPLICATION_NAME)
            request.set_timeout_in_seconds(600)
            SystemApplicationRemoveKeywords(self.ssh_connection).system_application_remove(request)
        elif current[1] not in ("uploaded", "upload-failed"):
            raise KeywordException(f"Application is still transitioning or unsupported: {current}")
        if self.original_application is None:
            request = SystemApplicationDeleteInput()
            request.set_app_name(APPLICATION_NAME)
            SystemApplicationDeleteKeywords(self.ssh_connection).get_system_application_delete(request)
        if SystemApplicationListKeywords(self.ssh_connection).get_application_state(APPLICATION_NAME) != self.original_application:
            raise KeywordException("Original application state was not restored")

    def capture_state(self, addfinalizer: Callable, exclusive: bool = False) -> None:
        """Snapshot baseline and register independent recovery before mutations.

        Args:
            addfinalizer (Callable): Pytest request.addfinalizer or equivalent registry.
            exclusive (bool): Lab is disposable and exclusively assigned to this run.
        """
        if self.captured:
            raise KeywordException("Policy state was already captured")
        self.application = SystemApplicationListKeywords(self.ssh_connection).get_application_state(APPLICATION_NAME)
        if not self.application or self.application[1] != "applied":
            raise KeywordException("Prepare an applied policy-operator baseline before capturing policy fixtures")
        self.policies = copy.deepcopy(self.policy_keywords.get_policies().get_policies())
        if not self.policies and not exclusive:
            raise KeywordException("Removing the last test policy requires an exclusive disposable lab")
        helm = SystemHelmOverrideKeywords(self.ssh_connection)
        self.charts = {}
        for chart in CHART_NAMES:
            observed = helm.get_system_helm_override_show(APPLICATION_NAME, chart, APPLICATION_NAME).get_helm_override_show()
            self.charts[chart] = {"attributes": observed.get_attributes(), "user_overrides": helm.get_user_override_values(APPLICATION_NAME, chart, APPLICATION_NAME)}
        nodes = KubernetesResourceListOutput(KubectlGetResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_resource_field("nodes", "", "{@}"))
        self.labels = nodes.get_labels("ipsec-policy-agent-operator")
        self.exclusive = exclusive
        addfinalizer(self.restore_state)
        self.captured = True

    def prepare_candidate(self, version: str, images: dict[str, dict[str, str]], provenance: dict[str, str], chart_overrides: dict[str, dict] | None = None) -> IPsecPolicyImagesOutput:
        """Apply explicit image/configuration overrides with baseline recovery.

        Use update_candidate_package after capture for a different package.
        Unchanged expected image digests are valid for metadata-only candidates.

        Args:
            version (str): Expected installed package version.
            images (dict[str, dict[str, str]]): Complete expected images by role.
            provenance (dict[str, str]): Application, automation and build references.
            chart_overrides (dict[str, dict] | None): Complete desired user values by chart.

        Returns:
            IPsecPolicyImagesOutput: Verified candidate identities.
        """
        if not self.captured:
            raise KeywordException("Capture baseline before preparing a candidate")
        if version != (self.candidate_package_version or self.application[0]):
            raise KeywordException("Install the configured candidate package with existing application APIs before fixture capture")
        if any(not provenance.get(key) for key in ("application_revision", "automation_revision", "build_reference")):
            raise KeywordException("Candidate provenance is required before mutation")
        if set(images) != {"agent", "manager"} or any(not values or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) for digest in values.values()) for values in images.values()):
            raise KeywordException("Complete immutable candidate image identities are required before mutation")
        if chart_overrides:
            if not self.exclusive or set(chart_overrides) - set(CHART_NAMES) or any(not isinstance(values, dict) for values in chart_overrides.values()):
                raise KeywordException("Chart mutation requires an exclusive lab and supported chart mappings")
            baseline_images = self.policy_keywords.get_running_images()
            # Reverse-order recovery restores each chart before reapplying it.
            self.add_cleanup("Reapply baseline", lambda: self._reapply_baseline(baseline_images))
            for chart in chart_overrides:
                self.add_cleanup(f"Restore {chart}", lambda chart=chart: self._set_chart_overrides(chart, self.charts[chart]["user_overrides"]))
            for chart, values in chart_overrides.items():
                self._set_chart_overrides(chart, values)
            SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply(APPLICATION_NAME)
        return self.policy_keywords.verify_candidate(version, images, provenance)

    def _write_owned_file(self, path: str, content: str) -> None:
        """Write an owned manifest privately and check the write exit status.

        Args:
            path (str): Registered temporary file.
            content (str): Exact manifest or override content.
        """
        self.ssh_connection.send(f"umask 077; printf %s {quote(content)} > {quote(path)}")
        self.validate_success_return_code(self.ssh_connection)

    def _set_chart_overrides(self, chart: str, values: dict) -> None:
        """Replace one chart's user overrides through existing Helm APIs.

        Args:
            chart (str): Selected policy chart.
            values (dict): Complete desired user values.
        """
        helm = SystemHelmOverrideKeywords(self.ssh_connection)
        if helm.get_user_override_values(APPLICATION_NAME, chart, APPLICATION_NAME) == values:
            return
        if not values:
            helm.delete_system_helm_override(APPLICATION_NAME, chart, APPLICATION_NAME)
        else:
            path = f"/tmp/{self.run_id}-override-{uuid4().hex}.yaml"
            self.files.append(path)
            self._write_owned_file(path, yaml.safe_dump(values))
            helm.update_helm_override(quote(path), APPLICATION_NAME, chart, APPLICATION_NAME, reuse_values=False)
        if helm.get_user_override_values(APPLICATION_NAME, chart, APPLICATION_NAME) != values:
            raise KeywordException(f"User overrides were not restored for {chart}")

    def _reapply_baseline(self, baseline_images: IPsecPolicyImagesOutput) -> None:
        """Reapply restored charts and verify baseline running images.

        Args:
            baseline_images (IPsecPolicyImagesOutput): Captured immutable images.
        """
        SystemApplicationApplyKeywords(self.ssh_connection).system_application_apply(APPLICATION_NAME)
        observed = self.policy_keywords.get_running_images()
        # Manager pod names change during a rollout; compare role/container
        # identity while agent node coverage remains checked by shared readiness.
        for role in ("agent", "manager"):
            expected = baseline_images.get_role_images(role)
            actual = observed.get_role_images(role)
            if actual != expected:
                raise KeywordException(f"Baseline {role} images were not restored")

    def add_cleanup(self, description: str, callback: Callable[[], None]) -> None:
        """Register an independent recovery action before its corresponding mutation.

        Args:
            description (str): Action description for failure diagnostics.
            callback (Callable[[], None]): Idempotent domain recovery operation.
        """
        if not self.captured:
            raise KeywordException("Capture baseline before registering mutations")
        self.cleanups.append((description, callback))

    def apply_owned_resource(self, manifest: dict) -> None:
        """Create or update only a run-owned resource using existing manifest APIs.

        Args:
            manifest (dict): Resource with this run's name prefix and ownership label.
        """
        if not self.captured:
            raise KeywordException("Capture baseline before mutation")
        manifest = copy.deepcopy(manifest)
        metadata = manifest.get("metadata", {})
        if not metadata.get("name", "").startswith(self.run_id) or metadata.get("labels", {}).get(OWNER_LABEL) != self.run_id:
            raise KeywordException("Refusing a resource without this run's explicit ownership")
        allowed_kinds = {"Namespace", "ConfigMap", "Pod", "Service", "IPsecPolicy"}
        if manifest.get("kind") not in allowed_kinds:
            raise KeywordException("Unsupported owned policy fixture resource")
        if manifest["kind"] in {"IPsecPolicy", "Namespace"}:
            if "namespace" in metadata:
                raise KeywordException("Policy and Namespace resources must be cluster scoped")
        elif metadata.get("namespace") != self.run_id:
            raise KeywordException("Fixture resources must use the owned namespace")
        current = self._find_owned_resource(manifest)
        if current is not None and current["metadata"].get("labels", {}).get(OWNER_LABEL) != self.run_id:
            raise KeywordException("Refusing to overwrite a resource owned by another actor")

        # Record intended cleanup before file creation or kubectl apply: a command
        # can succeed remotely even when its reply is lost.
        path = f"/tmp/{self.run_id}-{uuid4().hex}.json"
        self.files.append(path)
        self.resources.append(manifest)
        self._write_owned_file(path, json.dumps(manifest))
        KubectlFileApplyKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).apply_resource_from_yaml(quote(path))
        observed = self._find_owned_resource(manifest)
        if observed is None or observed.get_label(OWNER_LABEL) != self.run_id:
            raise KeywordException("Applied fixture ownership could not be verified")

    def _find_owned_resource(self, manifest: dict) -> KubernetesResourceObject | None:
        """Look up a fixture without swallowing API/transport errors.

        Args:
            manifest (dict): Desired resource identity.

        Returns:
            KubernetesResourceObject | None: Observed resource or confirmed absence.
        """
        metadata = manifest["metadata"]
        resource = POLICY_RESOURCE if manifest["kind"] == "IPsecPolicy" else manifest["kind"].lower()
        namespace = metadata.get("namespace")
        reader = KubectlGetResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path())
        if namespace:
            namespaces = KubernetesResourceListOutput(reader.get_resource_field("namespaces", "", "{@}"))
            if namespaces.find_resource(namespace) is None:
                return None
        resources = KubernetesResourceListOutput(reader.get_resource_field(resource, "", "{@}", quote(namespace) if namespace else None))
        return resources.find_resource(metadata["name"])

    def delete_owned_resource(self, manifest: dict) -> None:
        """Delete an owned fixture only after rechecking live ownership.

        Args:
            manifest (dict): Previously registered fixture resource.
        """
        if manifest not in self.resources:
            raise KeywordException("Refusing deletion of an unregistered resource")
        observed = self._find_owned_resource(manifest)
        if observed is None:
            return
        if observed.get_label(OWNER_LABEL) != self.run_id:
            raise KeywordException("Resource ownership changed; refusing deletion")
        if manifest["kind"] == "IPsecPolicy" and not self.exclusive and len(self.policy_keywords.get_policies().get_policies()) <= 1:
            raise KeywordException("Last-policy cleanup requires an exclusive disposable lab")
        path = f"/tmp/{self.run_id}-delete-{uuid4().hex}.json"
        self.files.append(path)
        self._write_owned_file(path, json.dumps(manifest))
        KubectlFileDeleteKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).delete_resources(quote(path), ignore_not_found=True)

    def verify_baseline(self) -> None:
        """Check that pre-existing app, policies, chart values and labels survived."""
        if SystemApplicationListKeywords(self.ssh_connection).get_application_state(APPLICATION_NAME) != self.application:
            raise KeywordException("Application baseline was not restored")
        policies = {item.get_name(): item for item in self.policy_keywords.get_policies().get_policies()}
        for baseline in self.policies:
            current = policies.get(baseline.get_name())
            if not current or current.get_uid() != baseline.get_uid() or current.get_spec() != baseline.get_spec():
                raise KeywordException("A pre-existing policy changed during validation")
        helm = SystemHelmOverrideKeywords(self.ssh_connection)
        for chart, baseline in self.charts.items():
            current = helm.get_system_helm_override_show(APPLICATION_NAME, chart, APPLICATION_NAME).get_helm_override_show()
            if current.get_attributes() != baseline["attributes"] or helm.get_user_override_values(APPLICATION_NAME, chart, APPLICATION_NAME) != baseline["user_overrides"]:
                raise KeywordException(f"Chart baseline was not restored: {chart}")
        nodes = KubernetesResourceListOutput(KubectlGetResourceKeywords(self.ssh_connection, self.k8s_config.get_kubeconfig_path()).get_resource_field("nodes", "", "{@}"))
        labels = nodes.get_labels("ipsec-policy-agent-operator")
        if labels != self.labels:
            raise KeywordException("Policy-agent node labels changed")
        self.policy_keywords.wait_for_agents_ready()

    def restore_state(self) -> None:
        """Attempt all independent recovery stages and report every failure."""
        errors = []
        for manifest in reversed(self.resources):
            try:
                self.delete_owned_resource(manifest)
            except Exception as error:
                errors.append(f"{manifest['kind']}/{manifest['metadata']['name']}: {error}")
        for description, callback in reversed(self.cleanups):
            try:
                callback()
            except Exception as error:
                errors.append(f"{description}: {error}")
        for path in self.files:
            try:
                FileKeywords(self.ssh_connection).delete_file(quote(path))
                self.validate_success_return_code(self.ssh_connection)
            except Exception as error:
                errors.append(f"File {path}: {error}")
        try:
            self.verify_baseline()
        except Exception as error:
            errors.append(f"Baseline verification: {error}")
        if errors:
            raise KeywordException("Policy fixture recovery failed: " + "; ".join(errors))
