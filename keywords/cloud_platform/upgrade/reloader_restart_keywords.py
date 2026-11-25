"""Reload-delivery check for the reloader platform-upgrade compatibility test.

reloader's only job is to react. A reloader that is installed, applied, running, annotated and
silently not reloading is indistinguishable from a healthy one by any readiness, version or alarm
check, so the functional truth here is not that reloader's own pods are up - it is that a change to
a watched ConfigMap and to a watched Secret still causes the consuming workload to be rolled, and
that the new pod actually receives the changed value.

Four things make this hard to pass vacuously, and each exists because the obvious version of it
passes when it should not.

The watched resources are consumed through envFrom, never a volume mount. The kubelet syncs
projected ConfigMap and Secret volumes in place, so a file read inside a running, never-restarted
container changes on its own - that assertion passes with reloader deleted.

The delivered value is asserted, not just the rollout. A rollout triggered by something else, an
unrelated reconcile or an operator sweep, satisfies a restart check and fails this one.

An unannotated negative control runs alongside the probe, consuming its own ConfigMap and Secret,
and must not move - while those resources are changed in the same apply. Both halves matter. Without
a control, nothing separates "reloader rolled the workload" from "something rolls workloads here";
and with a control whose resources never change, an annotation-blind reloader would still leave it
alone and pass, because the control watches nothing that moved.

All of it is decided on one settled snapshot after a single bounded wait, rather than as several
independent waits. A rollout in flight exposes the new pod's identity before it is ready, and
readiness before its environment can be read, so independent waits let the early facts pass and the
late ones fail on the same transient lag.

Note on diagnosis: validate_equals_with_retry raises TimeoutError when its window expires, so
assertions placed after it never run on a failing system. Every poll therefore logs the snapshot it
observed, which is what leaves something diagnosable in the run log instead of a bare timeout.
"""

from typing import Callable

from pytest import FixtureRequest

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from framework.validation.validation_response import ValidationResponse
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.registry.registry_image_resolver_keywords import RegistryImageResolverKeywords
from keywords.cloud_platform.upgrade.objects.reloader_rollout_readout import ReloaderRolloutReadout
from keywords.cloud_platform.upgrade.objects.workload_snapshot import ENV_VALUE_UNREADABLE, UID_UNREADABLE, WorkloadSnapshot
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords


class ReloaderRestartKeywords(BaseKeyword):
    """The reloader reload-delivery check, callable once per phase of a platform upgrade."""

    PROBE_TEMPLATE = "resources/cloud_platform/app_compat/reloader/reload-probe.yaml"
    NAMESPACE_PREFIX = "stxtest-reloader"
    PROBE_NAME = "reload-probe"
    CONTROL_NAME = "reload-control"
    # The pull secret a scratch namespace does not have. Without it the probe cannot pull its image
    # and never becomes ready, which reads as a reloader failure.
    PULL_SECRET = "default-registry-key"
    # The platform seeds the pull secret into kube-system, which is where the existing test cases
    # that need it in another namespace copy it from. The default namespace is not a source: on a
    # freshly configured system it holds no secrets at all, so copying from it fails setup before
    # any assertion runs.
    SOURCE_NAMESPACE = "kube-system"
    # Candidate probe images, in preference order. Discovered rather than pinned, because the
    # registry's contents differ between labs: a pinned reference fails to pull on a lab that does
    # not carry that image or that tag, and an unpullable probe looks exactly like the reload failure
    # this check exists to detect. Both the host prefix and the tag matter - a bare repository name
    # resolves to an implicit :latest against a public registry and fails the same way. The sibling
    # sidecar check records both as failures observed on hardware.
    PROBE_IMAGE_PREFERENCE = ("busybox", "alpine", "curlimages/curl", "ceph-config-helper")
    VALUE_KEY = "PROBE_CONFIGMAP_VALUE"
    SECRET_KEY = "PROBE_SECRET_VALUE"
    # Bounded wait for reloader to notice a watched change and the controller to finish the roll.
    # Hand-timed on an idle AIO-SX lab running reloader 26.10-4: three consecutive rounds, each
    # changing a watched ConfigMap and Secret together, completed in 29s, 30s and 29s measured from
    # the patch to the new pod reporting ready with both new values readable. The timeout keeps an
    # order-of-magnitude margin over that worst case, because the measurement was taken on an idle
    # single-node system while the test runs immediately after a platform upgrade, when the node is
    # still settling and a rollout can take substantially longer.
    ROLLOUT_TIMEOUT = 300
    ROLLOUT_POLL_INTERVAL = 10
    # How long the scratch probe and control pods get to come up. Shorter than ROLLOUT_TIMEOUT's
    # sibling budget in the test case, and deliberately so: these are two one-container pods pulling
    # an image already present in the local registry, not an application being moved to a new
    # release. The test case defines its own POD_READY_TIMEOUT, 900, for the reloader application's
    # own pod after a deploy, which has to pull the new release's image - a different wait that only
    # shares the name. Keeping the family's naming is intentional; istio and metrics-server pair the
    # same two names at the same two values, and the two never meet in one namespace because one is
    # a class attribute here and the other a module global there.
    POD_READY_TIMEOUT = 300
    POD_READY_POLL_INTERVAL = 10
    SERVICE_ACCOUNT_TIMEOUT = 120
    SERVICE_ACCOUNT_POLL_INTERVAL = 5
    NAMESPACE_DELETE_TIMEOUT = 300
    NAMESPACE_DELETE_INTERVAL = 10

    def __init__(self, ssh_connection: SSHConnection):
        """Instance of the class.

        Args:
            ssh_connection (SSHConnection): An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection
        self.create_namespace = KubectlCreateNamespacesKeywords(ssh_connection)
        self.delete_namespace = KubectlDeleteNamespaceKeywords(ssh_connection)
        self.get_namespaces = KubectlGetNamespacesKeywords(ssh_connection)
        self.yaml = YamlKeywords(ssh_connection)
        self.file_apply = KubectlFileApplyKeywords(ssh_connection)
        self.files = FileKeywords(ssh_connection)
        self.resources = KubectlGetResourceKeywords(ssh_connection)
        self.pods = KubectlGetPodsKeywords(ssh_connection)
        self.exec = KubectlExecInPodsKeywords(ssh_connection)
        self.get_secrets = KubectlGetSecretsKeywords(ssh_connection)
        self.create_secret = KubectlCreateSecretsKeywords(ssh_connection)
        self.image_resolver = RegistryImageResolverKeywords(ssh_connection)
        # One instance serves every phase of a test, so cleanup is tracked per phase.
        self._cleaned_up_phases = set()
        # Resolved on first use and reused for the life of the instance, so that every apply
        # in every phase renders the same image reference.
        self._probe_image = None

    def validate_reload_delivers(self, request: FixtureRequest, phase: str) -> None:
        """Assert reloader rolls a watched workload and delivers the change, at this phase.

        Creates a phase-scoped scratch namespace holding an annotated probe and an unannotated
        control, then changes the probe's watched ConfigMap and its watched Secret in turn. Each
        change must roll the probe, deliver the new value to the new pod, and leave the control
        untouched.

        Args:
            request (FixtureRequest): the pytest request, used to register cleanup before anything
                is created.
            phase (str): where in the upgrade this check is running, for example "pre" or
                "post-upgrade". Labels every assertion so the same failure is distinguishable
                between phases.
        """
        namespace = f"{self.NAMESPACE_PREFIX}-{phase}"
        # Registered before the namespace exists, so a setup that fails part way through still
        # cleans up. This ordering is the single most repeated lesson from the sibling checks.
        request.addfinalizer(self._cleanup_finalizer(phase, namespace))

        self._prepare_namespace(namespace, phase)
        configmap_value = f"{phase}-configmap-initial"
        secret_value = f"{phase}-secret-initial"
        self._apply_probe(namespace, phase, configmap_value, secret_value)

        get_logger().log_info(f"[{phase}] waiting for the probe and the control to become ready")
        baseline = self._wait_for_readable_snapshot(namespace, phase, configmap_value)

        configmap_value = f"{phase}-configmap-changed"
        get_logger().log_test_case_step(f"[{phase}] change the watched ConfigMap and require a delivered reload")
        self._apply_probe(namespace, phase, configmap_value, secret_value)
        baseline = self._assert_rolled(namespace, phase, "ConfigMap", baseline, configmap_value, secret_value)

        secret_value = f"{phase}-secret-changed"
        get_logger().log_test_case_step(f"[{phase}] change the watched Secret and require a delivered reload")
        self._apply_probe(namespace, phase, configmap_value, secret_value)
        self._assert_rolled(namespace, phase, "Secret", baseline, configmap_value, secret_value)

        self._delete_namespace_and_confirm(namespace, phase)
        self._mark_cleaned_up(phase)

    def _assert_rolled(self, namespace: str, phase: str, kind: str, baseline: ReloaderRolloutReadout, configmap_value: str, secret_value: str) -> ReloaderRolloutReadout:
        """Wait for one settled snapshot that satisfies every fact, then assert each of them.

        One shared window rather than a wait per fact: a rollout in flight exposes the new pod's
        identity before it is ready, and readiness before its environment can be read, so
        independent waits would let the early facts pass and the late ones fail on the same
        transient lag.

        Args:
            namespace (str): the scratch namespace.
            phase (str): the upgrade phase label.
            kind (str): "ConfigMap" or "Secret", naming which watch path was exercised.
            baseline (ReloaderRolloutReadout): the snapshot taken before the change.
            configmap_value (str): the value now written to the watched ConfigMap.
            secret_value (str): the value now written to the watched Secret.

        Returns:
            ReloaderRolloutReadout: the settled snapshot, for use as the next baseline.
        """
        expected = configmap_value if kind == "ConfigMap" else secret_value
        env_key = self.VALUE_KEY if kind == "ConfigMap" else self.SECRET_KEY

        def _poll() -> ValidationResponse:
            """Read one snapshot and report both the verdict and the snapshot it came from.

            Returning a ValidationResponse is what lets the caller keep the snapshot that actually
            satisfied the predicate. Reading again afterwards would discard it, and a single
            transient read failure in that second read would then produce a false failure in the
            next phase - the snapshot it returned would carry sentinels that nothing had validated.

            Returns:
                ValidationResponse: the verdict to match on, and the snapshot to hand back.
            """
            observed = self._read_snapshot(namespace, phase, env_key)
            return ValidationResponse(observed.is_rolled_from(baseline, expected), observed)

        # NOT COVERED BY A UNIT TEST, and deliberately left that way rather than covered badly.
        # The defect this guards against - re-reading after the window and handing an unvalidated
        # snapshot to the next phase - can only be exercised by failing a read at one exact point in
        # the run. The retry window is time-based, so the number of polls before that point varies
        # between runs and any budget measured in one run is wrong in the next. A test tuned to a
        # poll count would be flaky, and a flaky test here would be worse than none, which is what
        # the sibling checks' own notes say about hand-tuned waits. The reasoning stands on the
        # framework contract instead: validate_equals_with_retry returns the value_to_return of the
        # ValidationResponse that matched, so the snapshot handed back is by construction the one
        # that satisfied the predicate.

        # Nothing is asserted after this window, deliberately. validate_equals_with_retry raises
        # TimeoutError when it expires, so any assertion placed after it runs only when the window
        # already succeeded, where it is tautological and cannot fail. Diagnosis comes instead from
        # _read_snapshot, which logs each snapshot as it polls and so leaves the last observed state
        # in the run log.
        return validate_equals_with_retry(
            _poll,
            True,
            f"[{phase}] the {kind} change must roll the probe and deliver the new value, leaving the control unmoved",
            timeout=self.ROLLOUT_TIMEOUT,
            polling_sleep_time=self.ROLLOUT_POLL_INTERVAL,
        )

    def _wait_for_readable_snapshot(self, namespace: str, phase: str, configmap_value: str) -> ReloaderRolloutReadout:
        """Wait until both workloads are up and every read completes, and return that snapshot.

        Args:
            namespace (str): the scratch namespace.
            phase (str): the upgrade phase label.
            configmap_value (str): the value written to the watched ConfigMap, asserted as the
                value the probe starts life observing.

        Returns:
            ReloaderRolloutReadout: the baseline snapshot.
        """

        def _poll() -> ValidationResponse:
            """Read one snapshot and report whether both workloads are up, and the snapshot itself.

            Returns:
                ValidationResponse: the verdict to match on, and the snapshot to hand back.
            """
            observed = self._read_snapshot(namespace, phase, self.VALUE_KEY)
            settled = observed.is_readable() and observed.get_probe().is_ready() and observed.get_control().is_ready()
            return ValidationResponse(settled, observed)

        baseline = validate_equals_with_retry(
            _poll,
            True,
            f"[{phase}] the probe and the control must come up and become readable",
            timeout=self.POD_READY_TIMEOUT,
            polling_sleep_time=self.POD_READY_POLL_INTERVAL,
        )
        # Readiness is part of the wait above rather than an assertion here. A running container can
        # be exec'd into before its pod reports ready, so the environment becomes readable first;
        # asserting readiness at that moment fails a system that was one poll away from ready.
        validate_equals(baseline.get_env_value(), configmap_value, f"[{phase}] the probe must observe its initial ConfigMap value")
        return baseline

    def _read_snapshot(self, namespace: str, phase: str, env_key: str) -> ReloaderRolloutReadout:
        """Take one snapshot of the probe and the control, and log it.

        Never raises: the caller is a retry wrapper, which retries values rather than catching
        exceptions. Each read degrades to its sentinel instead.

        The log line is not decoration. validate_equals_with_retry raises TimeoutError when its
        window expires, so the assertions after it never run on a failing system and the retry's own
        log reports only "Observed: False". Logging the snapshot per poll is what leaves a diagnosis
        behind.

        Args:
            namespace (str): the scratch namespace.
            phase (str): the upgrade phase label.
            env_key (str): which environment variable to read from the probe pod - the ConfigMap
                variable or the Secret one, depending on the watch path under test.

        Returns:
            ReloaderRolloutReadout: the paired snapshot.
        """
        probe_pod = self._read_pod_name(namespace, self.PROBE_NAME)
        control_pod = self._read_pod_name(namespace, self.CONTROL_NAME)
        probe = WorkloadSnapshot(
            self._read_pod_uid(namespace, probe_pod),
            self._read_field(namespace, self.PROBE_NAME, "{.metadata.generation}"),
            self._read_field(namespace, self.PROBE_NAME, "{.status.observedGeneration}"),
            self._read_pod_ready(namespace, self.PROBE_NAME),
        )
        control = WorkloadSnapshot(
            self._read_pod_uid(namespace, control_pod),
            self._read_field(namespace, self.CONTROL_NAME, "{.metadata.generation}"),
            self._read_field(namespace, self.CONTROL_NAME, "{.status.observedGeneration}"),
            self._read_pod_ready(namespace, self.CONTROL_NAME),
        )
        readout = ReloaderRolloutReadout(probe, control, self._read_env_value(namespace, probe_pod, env_key))
        get_logger().log_info(f"[{phase}] {readout}")
        return readout

    def _read_pod_name(self, namespace: str, label: str) -> str:
        """Return the single pod of a labelled workload, or an empty string.

        The probe runs one replica with the Recreate strategy, so more than one pod means a rollout
        is still in flight and the snapshot is not usable yet. Returning empty rather than guessing
        avoids reading the outgoing pod, which is what makes an items[0] read unreliable.

        Args:
            namespace (str): the namespace.
            label (str): the workload's app label value.

        Returns:
            str: the pod name, or an empty string when there is not exactly one.
        """
        try:
            pods = self.pods.get_pods(namespace=namespace, label=f"app={label}").get_pods()
        except Exception:  # noqa: BLE001 - a transient kubectl failure must keep the window going
            return ""
        if len(pods) != 1:
            return ""
        return pods[0].get_name()

    def _read_pod_uid(self, namespace: str, pod_name: str) -> str:
        """Return a pod's UID, degrading to the sentinel.

        Args:
            namespace (str): the namespace.
            pod_name (str): the pod name, possibly empty.

        Returns:
            str: the UID, or UID_UNREADABLE.
        """
        if not pod_name:
            return UID_UNREADABLE
        try:
            return self.pods.get_pod_uid_by_name(pod_name, namespace) or UID_UNREADABLE
        except Exception:  # noqa: BLE001 - get_pod_uid_by_name raises when the pod has gone
            return UID_UNREADABLE

    def _read_pod_ready(self, namespace: str, label: str) -> str:
        """Return a workload's pod READY string, such as "1/1".

        Args:
            namespace (str): the namespace.
            label (str): the workload's app label value.

        Returns:
            str: the READY value, or an empty string when unreadable.
        """
        try:
            pods = self.pods.get_pods(namespace=namespace, label=f"app={label}").get_pods()
        except Exception:  # noqa: BLE001
            return ""
        if len(pods) != 1:
            return ""
        return pods[0].get_ready()

    def _read_field(self, namespace: str, deployment: str, jsonpath: str) -> str:
        """Read one field from a Deployment, degrading to an empty string.

        get_resource_field raises on a failed kubectl get, and the first read after a change can
        fail while the apiserver settles. A raise here would end the run with its timeout budget
        unspent.

        Args:
            namespace (str): the namespace.
            deployment (str): the Deployment name.
            jsonpath (str): the jsonpath expression.

        Returns:
            str: the field value, or an empty string.
        """
        try:
            return self.resources.get_resource_field("deployment", deployment, jsonpath, namespace=namespace)
        except Exception:  # noqa: BLE001
            return ""

    def _read_env_value(self, namespace: str, pod_name: str, key: str) -> str:
        """Read one environment variable from inside the probe pod.

        printenv exits 1 when the variable is unset, and the exec keyword asserts the return code by
        default, so both are suppressed: ignore_error stops the keyword asserting and the shell's
        `|| true` stops a non-zero exit propagating. The jsonpath behaviour elsewhere in this file -
        kubectl exits 0 for an absent key - does not carry over to exec, so a bare read would raise
        inside the retry window on every poll before the roll completed.

        The return code is then inspected rather than ignored, which is what ignore_error leaves the
        caller to do. It has to be, for two reasons that compound: the SSH layer folds stderr into
        stdout, so a failed exec returns its error text in place of a value, and that text is not
        empty - so without this check it is indistinguishable from a successful read. A pod exists
        before its container does, so an exec during the pull fails, and the error text would be
        taken for a value, make the snapshot look readable and end the readiness wait early. The
        inner `|| true` means a genuinely unset variable still exits zero, so the return code
        separates a failed read from an unset variable rather than conflating them.

        Read from inside the running container rather than with
        KubectlGetPodConfigKeywords.get_pod_env_value, which was considered and rejected. That
        keyword reads the pod's container spec, so it reports what the workload was declared to
        receive rather than what the container actually holds, and this check exists to prove
        delivery rather than intent. These values also arrive through envFrom, which a spec-level
        read of individual env entries does not see at all.

        Args:
            namespace (str): the namespace.
            pod_name (str): the probe pod name, possibly empty.
            key (str): the variable to read, named by the caller because only the caller knows
                which watch path this phase is exercising.

        Returns:
            str: the value, or ENV_VALUE_UNREADABLE.
        """
        if not pod_name:
            return ENV_VALUE_UNREADABLE
        try:
            output = self.exec.run_pod_exec_cmd(pod_name, f"sh -c 'printenv {key} || true'", options=f"-n {namespace}", ignore_error=True)
        except Exception:  # noqa: BLE001
            return ENV_VALUE_UNREADABLE
        if self.ssh_connection.get_return_code() != 0:
            return ENV_VALUE_UNREADABLE
        value = (output[0] if isinstance(output, list) and output else str(output or "")).strip()
        return value or ENV_VALUE_UNREADABLE

    def _apply_probe(self, namespace: str, phase: str, configmap_value: str, secret_value: str) -> None:
        """Render and apply the probe and control manifest with the given watched values.

        Re-applying the same manifest with a changed value is what exercises reloader: the ConfigMap
        or Secret content differs, reloader notices, and the annotated workload is re-templated. The
        control's own ConfigMap and Secret change in the same apply, and the control must still not
        move - that is what makes the rollout attributable to the annotation rather than to the
        apply. Holding the control's values constant would prove nothing.

        Args:
            namespace (str): the scratch namespace.
            phase (str): the upgrade phase label.
            configmap_value (str): the value to write to the probe's watched ConfigMap.
            secret_value (str): the value to write to the probe's watched Secret.
        """
        replacements = {
            "namespace": namespace,
            "probe_name": self.PROBE_NAME,
            "control_name": self.CONTROL_NAME,
            "pull_secret": self.PULL_SECRET,
            "image": self._discover_probe_image(),
            "value_key": self.VALUE_KEY,
            "secret_key": self.SECRET_KEY,
            "configmap_value": configmap_value,
            "secret_value": secret_value,
            # The control's own resources change in lockstep with the probe's, and this is the
            # whole point of the control. Held constant they would prove nothing: a reloader that
            # ignored annotations entirely would still leave the control alone, because the control
            # does not watch anything that moved. Changing them means a correct reloader must
            # distinguish the two workloads by annotation, and an annotation-blind one rolls both
            # and fails. With constant control values an annotation-blind reloader satisfies every
            # assertion in this check, which is the hole this closes.
            "control_configmap_value": f"control-{configmap_value}",
            "control_secret_value": f"control-{secret_value}",
        }
        rendered = self.yaml.generate_yaml_file_from_template(
            get_stx_resource_path(self.PROBE_TEMPLATE),
            replacements,
            f"reload-probe-{phase}.yaml",
            "/home/sysadmin",
        )
        self.file_apply.apply_resource_from_yaml(rendered)

    def _discover_probe_image(self) -> str:
        """Resolve the probe image once, and reuse it for the life of this instance.

        Resolution itself lives in RegistryImageResolverKeywords; what is local here is the caching
        and the reason for it. The reference is substituted into both the annotated probe and the
        unannotated control, and _apply_probe runs three times per phase, so a reference that
        changed between applies would re-template the control, advance its generation and fail the
        phase reporting that reloader had ignored annotations.

        Returns:
            str: a fully qualified image reference, host and tag included.
        """
        if self._probe_image is not None:
            return self._probe_image
        self._probe_image = self.image_resolver.resolve_image_reference(self.PROBE_IMAGE_PREFERENCE)
        return self._probe_image

    def _prepare_namespace(self, namespace: str, phase: str) -> None:
        """Create the scratch namespace and make it able to run the probe.

        Args:
            namespace (str): the namespace to create.
            phase (str): the upgrade phase label.
        """
        if self.get_namespaces.get_namespaces().is_namespace(namespace):
            get_logger().log_info(f"[{phase}] removing a leftover namespace {namespace}")
            self._delete_namespace_and_confirm(namespace, phase)
        self.create_namespace.create_namespaces(namespace)
        self._wait_for_default_service_account(namespace, phase)
        self._ensure_pull_secret(namespace)

    def _wait_for_default_service_account(self, namespace: str, phase: str) -> None:
        """Wait for the namespace's default ServiceAccount before any pod is created.

        A pod created before the ServiceAccount controller has caught up is rejected at admission,
        which surfaces as an error on the create rather than as a pod condition, so no amount of
        pod-level retrying recovers from it. This cost the istio check a flaky run that three green
        runs had hidden.

        Args:
            namespace (str): the namespace.
            phase (str): the upgrade phase label.
        """
        validate_equals_with_retry(
            lambda: self._read_default_service_account_exists(namespace),
            True,
            f"[{phase}] the namespace's default ServiceAccount must exist before any pod is created",
            timeout=self.SERVICE_ACCOUNT_TIMEOUT,
            polling_sleep_time=self.SERVICE_ACCOUNT_POLL_INTERVAL,
        )

    def _read_default_service_account_exists(self, namespace: str) -> bool:
        """Report whether the namespace's default ServiceAccount is present.

        Args:
            namespace (str): the namespace.

        Returns:
            bool: True when it exists.
        """
        try:
            return bool(self.resources.get_resource_field("serviceaccount", "default", "{.metadata.name}", namespace=namespace))
        except Exception:  # noqa: BLE001
            return False

    def _ensure_pull_secret(self, namespace: str) -> None:
        """Copy the local registry pull secret into the scratch namespace.

        Args:
            namespace (str): the namespace.
        """
        if self.PULL_SECRET in self.get_secrets.get_secret_names(namespace):
            return
        self.create_secret.copy_secret_between_namespaces(self.PULL_SECRET, self.SOURCE_NAMESPACE, namespace)

    def _delete_namespace_and_confirm(self, namespace: str, phase: str) -> None:
        """Delete the scratch namespace and assert it is gone.

        The asserting verb is used rather than the tolerant one: a namespace stuck Terminating is a
        leaked resource that the next phase would then collide with, so cleanup failure fails the
        test rather than warning.

        Args:
            namespace (str): the namespace.
            phase (str): the upgrade phase label.
        """
        self.delete_namespace.delete_namespace(namespace)
        validate_equals_with_retry(
            lambda: self.get_namespaces.get_namespaces().is_namespace(namespace),
            False,
            f"[{phase}] the scratch namespace must be removed",
            timeout=self.NAMESPACE_DELETE_TIMEOUT,
            polling_sleep_time=self.NAMESPACE_DELETE_INTERVAL,
        )
        self.files.delete_file(f"/home/sysadmin/reload-probe-{phase}.yaml")

    def _cleanup_finalizer(self, phase: str, namespace: str) -> Callable[[], None]:
        """Return a finalizer that removes this phase's namespace unless the phase already did.

        Args:
            phase (str): the upgrade phase label.
            namespace (str): the namespace to remove.

        Returns:
            Callable[[], None]: the finalizer.
        """

        def _finalizer() -> None:
            """Remove the phase's scratch namespace if its own happy path did not."""
            if phase in self._cleaned_up_phases:
                return
            get_logger().log_teardown_step(f"[{phase}] remove the scratch namespace {namespace}")
            # Tolerant here, asserting on the happy path, for two separate reasons. The finalizer is
            # registered before the namespace exists - which is what makes a setup failure safe - so
            # it can legitimately run with nothing to remove. And a phase that failed is the case
            # most likely to leave the namespace wedged in Terminating, where the asserting verb
            # would spend its whole timeout and then raise a teardown error over the real failure.
            if self.get_namespaces.get_namespaces().is_namespace(namespace):
                self.delete_namespace.cleanup_namespace(namespace)
            self._mark_cleaned_up(phase)

        return _finalizer

    def _mark_cleaned_up(self, phase: str) -> None:
        """Record that a phase has cleaned up, so its finalizer does nothing.

        Args:
            phase (str): the upgrade phase label.
        """
        self._cleaned_up_phases.add(phase)
