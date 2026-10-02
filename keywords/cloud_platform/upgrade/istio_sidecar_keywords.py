import time
from typing import Callable

from pytest import FixtureRequest

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_str_contains
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.registry.system_registry_image_list_keywords import SystemRegistryImageListKeywords
from keywords.cloud_platform.system.registry.system_registry_image_tags_keywords import SystemRegistryImageTagsKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.namespace.kubectl_label_namespace_keywords import KubectlLabelNamespaceKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords


class IstioSidecarKeywords(BaseKeyword):
    """This class contains the istio sidecar-injection check.

    The functional truth for istio is that the sidecar injector still injects a working sidecar.
    Checking that the istio pods are running proves considerably less: the platform up-versions the
    application during deploy activate, and a control plane that comes back up without a functioning
    injector looks healthy by pod count while the mesh is broken for every workload.

    The check is deliberately blind to the istio version. It records the injected sidecar image tag
    and the caller compares it across upgrade phases, so nothing here needs updating when the
    release ships a new istio.

    Where the sidecar lives is NOT assumed, and it is NOT predictable from the istio version. istio
    made native sidecars the default in 1.27, but that does not decide the layout here: measured
    on hardware, the same istio 1.29.2 injected istio-proxy as an init container when the platform
    was upgraded from one release back and as a regular container when upgraded from two releases
    back. The layout follows the injector configuration carried through the upgrade, not the proxy
    version. Both container lists are read, and readiness is asserted by comparing the ready count
    against the total rather than by deriving an expected count, since an injected pod reads 2/2 in
    both layouts. A check that read only spec.containers would pass its negative control vacuously
    and fail its positive one on a perfectly healthy control plane.

    Each observed run was internally consistent - every phase of a run saw the same layout - but
    nothing guarantees that, precisely because the layout comes from configuration rather than from
    the version. So no constant is assumed within a run either.

    Artifacts are created in a phase-scoped scratch namespace and removed afterwards. The namespace
    is phase-scoped rather than shared, because the injection label lives on the namespace itself:
    the check asserts that a pod created BEFORE labelling gets no sidecar, and that assertion is
    only meaningful in a namespace that has never been labelled.
    """

    SIDECAR_CONTAINER = "istio-proxy"
    SIDECAR_IMAGE_MARKER = "proxyv2"
    INJECTION_LABEL_KEY = "istio-injection"
    INJECTION_LABEL_VALUE = "enabled"
    MULTUS_ANNOTATION_VALUE = "istio-cni"
    NAMESPACE_PREFIX = "stxtest-istio"
    PULL_SECRET_NAME = "stxtest-istio-regcred"
    # The injector is configured to add this pull secret to every injected pod - it is the
    # namespace needs it too. Observed on a 26.03 AIO-SX as "Unable to retrieve some image pull
    # secrets (default-registry-key)" on the injected probe pod.
    INJECTED_PULL_SECRET_NAME = "default-registry-key"

    # Any tiny image with a shell will do; the probe only needs a container that stays up long
    # enough to be inspected. Searched in this order against whatever the local registry actually
    # holds, because pinning an image makes the check fail on a lab whose registry differs.
    #
    # Every candidate here MUST have /bin/sh, because the probe pod overrides the command with a
    # shell sleep. 'pause' is deliberately absent for that reason: it is present on every
    # Kubernetes node and would therefore be chosen first, but it is a scratch image with no shell,
    # so the override would fail the container and the failure would look like a sidecar problem.
    #
    # busybox and alpine come first because they are purpose-built for this, but neither ships with
    # the platform - they are only present if somebody pushed them. curlimages/curl and
    # ceph-config-helper are both on a default install and both carry a shell, curl being
    # Alpine-based and the smaller of the two. Verified against a 26.03 AIO-SX, whose registry held
    # curlimages/curl:8.17.0 and no busybox or alpine at all.
    SLEEPER_IMAGE_PREFERENCE = ("busybox", "alpine", "curlimages/curl", "ceph-config-helper")

    POD_READY_TIMEOUT = 300
    POD_READY_POLL_INTERVAL = 10
    NAMESPACE_DELETE_TIMEOUT = 300
    NAMESPACE_DELETE_INTERVAL = 10

    # A freshly created namespace does not have its 'default' ServiceAccount immediately: the
    # service-account controller creates it asynchronously. Creating a pod before it exists is
    # rejected outright with
    #   pods "..." is forbidden: error looking up service account <ns>/default:
    #   serviceaccount "default" not found
    # which is a hard error, not a retryable pod condition, so it fails the phase immediately.
    # Observed on a 25.09 AIO-SX post-upgrade; the same code had passed repeatedly on labs where
    # the controller happened to win the race, which is exactly what makes it worth an explicit
    # wait rather than a retry around the apply.
    DEFAULT_SERVICE_ACCOUNT = "default"
    SERVICE_ACCOUNT_TIMEOUT = 120
    SERVICE_ACCOUNT_POLL_INTERVAL = 5

    # istio validates pod creation through a mutating admission webhook served by istiod, under
    # failurePolicy Fail. After a platform upgrade or rollback istiod is recreated, and for a window
    # it is Running and Ready while the webhook is not yet answering. A create in that window says
    # nothing about whether istio works, only that it was asked too early, so it is retried for a
    # bounded period. Unlike cert-manager's equivalent this matches on ANY of the markers rather
    # than all of them: istio reports this condition with several different messages and requiring
    # all of them would mean never retrying at all.
    WEBHOOK_READY_TIMEOUT = 180
    WEBHOOK_POLL_INTERVAL = 10
    WEBHOOK_UNAVAILABLE_MARKERS = (
        "failed calling webhook",
        "connection refused",
        "no endpoints available",
        "context deadline exceeded",
        "i/o timeout",
        "service unavailable",
        "EOF",
    )

    # Returned by the readiness reader when the pod cannot be read at all, so a transient kubectl
    # failure keeps the caller's wait going instead of raising out of a retry wrapper that only
    # retries on a value. Negative-looking so it cannot be mistaken for a real ready string.
    POD_STATE_UNREADABLE = "<unreadable>"

    NAD_TEMPLATE = "resources/cloud_platform/app_compat/istio/istio-cni-nad.yaml"
    POD_TEMPLATE = "resources/cloud_platform/app_compat/istio/injection-test-pod.yaml"

    # Filters use DOUBLE quotes inside the expression on purpose. Both readers interpolate the
    # jsonpath into a single-quoted shell argument, so a filter written with single quotes is
    # silently destroyed by the shell before kubectl ever sees it.
    JSONPATH_METADATA_NAME = "{.metadata.name}"
    JSONPATH_CONTAINERS = "{.spec.containers[*].name}"
    JSONPATH_INIT_CONTAINERS = "{.spec.initContainers[*].name}"
    JSONPATH_SIDECAR_IMAGE = '{.spec.containers[?(@.name=="istio-proxy")].image}'
    JSONPATH_SIDECAR_IMAGE_INIT = '{.spec.initContainers[?(@.name=="istio-proxy")].image}'
    JSONPATH_MULTUS_ANNOTATION = r"{.metadata.annotations.k8s\.v1\.cni\.cncf\.io/networks}"

    def __init__(self, ssh_connection: SSHConnection):
        """Instance of the class.

        Args:
            ssh_connection (SSHConnection): An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection
        self.create_namespace = KubectlCreateNamespacesKeywords(ssh_connection)
        self.delete_namespace = KubectlDeleteNamespaceKeywords(ssh_connection)
        self.get_namespaces = KubectlGetNamespacesKeywords(ssh_connection)
        self.label_namespace = KubectlLabelNamespaceKeywords(ssh_connection)
        self.yaml = YamlKeywords(ssh_connection)
        self.file_apply = KubectlFileApplyKeywords(ssh_connection)
        self.files = FileKeywords(ssh_connection)
        self.resources = KubectlGetResourceKeywords(ssh_connection)
        self.pods = KubectlGetPodsKeywords(ssh_connection)
        self.create_secret = KubectlCreateSecretsKeywords(ssh_connection)
        self.get_secrets = KubectlGetSecretsKeywords(ssh_connection)
        self.registry_images = SystemRegistryImageListKeywords(ssh_connection)
        self.registry_tags = SystemRegistryImageTagsKeywords(ssh_connection)
        # One instance serves every phase of a test, so cleanup is tracked per phase.
        self._cleaned_up_phases = set()

    def validate_sidecar_is_injected(self, request: FixtureRequest, phase: str) -> str:
        """Assert istio injects a working sidecar, and return the sidecar image tag.

        Args:
            request (FixtureRequest): pytest request object, used to register cleanup for the failure path.
            phase (str): where in the upgrade this check is running, used to name artifacts so
                repeated runs do not collide, for example "pre" or "post-upgrade".

        Returns:
            str: the tag of the injected sidecar image, for the caller to compare across phases.
        """
        namespace = f"{self.NAMESPACE_PREFIX}-{phase}"
        unlabelled_pod = f"probe-unlabelled-{phase}"
        injected_pod = f"probe-injected-{phase}"
        generated_files = []

        # Registered BEFORE the namespace is prepared, not after. Preparing it includes waiting for
        # the namespace's ServiceAccount, which can time out, and anything that raises inside
        # _prepare_namespace would otherwise leave a created namespace with no finalizer to remove
        # it - poisoning every later run on that lab, which is the exact failure the pre-clean in
        # _prepare_namespace exists to recover from. The finalizer is tolerant of a namespace that
        # was never created, so registering it early costs nothing.
        #
        # Registered per phase, and skipped when that phase already cleaned up on its happy path.
        # Tracked per phase rather than in one attribute because a single keyword instance serves
        # every phase: a later phase resetting a shared flag would make an earlier phase's finalizer
        # believe its namespace still existed and delete it again, logging a misleading error.
        request.addfinalizer(self._cleanup_finalizer(phase, namespace))
        self._prepare_namespace(namespace, phase)

        sleep_image = self._discover_sleeper_image()
        self._ensure_pull_secret(namespace)

        # The negative control. A pod created before the namespace is labelled must come up with no
        # sidecar - and must come up, otherwise "no sidecar was injected" is indistinguishable from
        # "the image could not be pulled", which is the failure this check is most likely to hit
        # first on a new lab.
        unlabelled_file = self._render_pod(namespace, unlabelled_pod, sleep_image, phase)
        generated_files.append(unlabelled_file)
        self.file_apply.apply_resource_from_yaml(unlabelled_file)
        self._validate_pod_is_ready(namespace, unlabelled_pod, phase, "unlabelled probe pod")
        validate_equals(
            self._sidecar_is_present(namespace, unlabelled_pod),
            False,
            f"[{phase}] a pod created before the namespace is labelled must have no {self.SIDECAR_CONTAINER} container",
        )

        # The NAD is required, not optional. The platform configures the sidecar injector to add a
        # Multus annotation naming a NetworkAttachmentDefinition called istio-cni, resolved in the
        # pod's own namespace, so without it an injected pod never leaves Init. It is applied before
        # labelling, and it is not subject to any istio webhook, so it is applied plainly.
        nad_file = self.yaml.generate_yaml_file_from_template(
            get_stx_resource_path(self.NAD_TEMPLATE),
            {"namespace": namespace},
            f"istio-cni-nad-{phase}.yaml",
            "/tmp",
        )
        generated_files.append(nad_file)
        self.file_apply.apply_resource_from_yaml(nad_file)

        self.label_namespace.label_namespace(namespace, self.INJECTION_LABEL_KEY, self.INJECTION_LABEL_VALUE)

        # The create itself is an assertion: under failurePolicy Fail it cannot succeed while istiod
        # is unreachable.
        injected_file = self._render_pod(namespace, injected_pod, sleep_image, phase)
        generated_files.append(injected_file)
        self._apply_awaiting_webhook(injected_file, phase)

        validate_equals(
            self._sidecar_is_present(namespace, injected_pod),
            True,
            f"[{phase}] istio must inject a {self.SIDECAR_CONTAINER} container into a pod in a labelled namespace",
        )
        self._validate_pod_is_ready(namespace, injected_pod, phase, "injected probe pod")

        # Assert the value, not merely that something came back. kubectl defaults to
        # --allow-missing-template-keys=true, so an absent annotation reads as an empty string with
        # a zero return code and a non-emptiness check would pass on a pod that never got it.
        annotation = self.resources.get_resource_field("pod", injected_pod, self.JSONPATH_MULTUS_ANNOTATION, namespace=namespace)
        validate_equals(
            annotation,
            self.MULTUS_ANNOTATION_VALUE,
            f"[{phase}] the injected pod must carry the Multus annotation k8s.v1.cni.cncf.io/networks",
        )

        # Assert on the raw image string before extracting the tag. Deriving the tag first and
        # asserting on that would pass a digest-pinned or untagged image through as stable garbage,
        # which then compares equal across phases and reports a rollback as correct.
        sidecar_image = self._sidecar_image(namespace, injected_pod)
        validate_str_contains(
            sidecar_image,
            self.SIDECAR_IMAGE_MARKER,
            f"[{phase}] the injected sidecar must run the {self.SIDECAR_IMAGE_MARKER} image",
        )
        sidecar_tag = sidecar_image.rsplit(":", 1)[-1]
        get_logger().log_info(f"[{phase}] istio sidecar image {sidecar_image}, tag {sidecar_tag}")

        # Remove the artifacts now rather than at test teardown, and assert the removal. The
        # tolerant cleanup verb is used where a failure to remove is not itself a result - the
        # pre-clean, where a leftover namespace may simply not exist, and the finalizer, which runs
        # after a failure. Here on the happy path a namespace stuck Terminating IS a real failure,
        # and reporting it as a warning would let the next phase create its artifacts against a
        # half-deleted namespace.
        self._delete_namespace_and_confirm(namespace, phase)
        self._mark_cleaned_up(phase)
        for generated_file in generated_files:
            self._remove_generated_file(generated_file)

        return sidecar_tag

    def _prepare_namespace(self, namespace: str, phase: str) -> None:
        """Remove any leftover scratch namespace, then create it.

        The namespace is phase-scoped and the create asserts, so without a pre-clean a single
        interrupted run would poison every later run of this test on the same lab. Deletion is
        asynchronous, so the wait is not optional: creating into a Terminating namespace fails.

        Reusing a leftover namespace instead of replacing it is not an option. It may still carry
        the injection label, which would destroy the negative control.

        Creating the namespace is not sufficient on its own: its 'default' ServiceAccount is
        provisioned asynchronously, and a pod created before it exists is rejected outright. The
        wait for it is therefore part of preparing the namespace, not of creating the pod.

        Args:
            namespace (str): the scratch namespace for this phase.
            phase (str): the phase, for logging.
        """
        self.delete_namespace.cleanup_namespace(namespace)
        self.get_namespaces.wait_for_namespace_deleted(namespace, timeout=self.NAMESPACE_DELETE_TIMEOUT, interval=self.NAMESPACE_DELETE_INTERVAL)
        get_logger().log_info(f"[{phase}] creating scratch namespace {namespace}")
        self.create_namespace.create_namespaces(namespace)
        self._wait_for_default_service_account(namespace, phase)

    def _wait_for_default_service_account(self, namespace: str, phase: str) -> None:
        """Wait for a namespace's 'default' ServiceAccount to be provisioned.

        Kubernetes creates it asynchronously, so a pod applied too soon after the namespace is
        rejected with 'serviceaccount "default" not found'. That is a hard admission error rather
        than a pod condition, so it cannot be waited out further down and has to be prevented here.

        Args:
            namespace (str): the namespace to check.
            phase (str): the phase, for the failure message.
        """
        validate_equals_with_retry(
            lambda: self._read_default_service_account_exists(namespace),
            True,
            f"[{phase}] the namespace's '{self.DEFAULT_SERVICE_ACCOUNT}' ServiceAccount must be provisioned before pods are created",
            timeout=self.SERVICE_ACCOUNT_TIMEOUT,
            polling_sleep_time=self.SERVICE_ACCOUNT_POLL_INTERVAL,
        )

    def _read_default_service_account_exists(self, namespace: str) -> bool:
        """Report whether a namespace's 'default' ServiceAccount exists, without raising.

        This runs inside validate_equals_with_retry, which retries on a value and does not catch
        exceptions. A missing ServiceAccount makes kubectl exit non-zero, which the underlying read
        turns into an assertion, so the error has to be absorbed here and reported as False -
        otherwise the very condition being waited for would end the wait.

        Args:
            namespace (str): the namespace to check.

        Returns:
            bool: True when the ServiceAccount is present.
        """
        try:
            name = self.resources.get_resource_field(
                "serviceaccount",
                self.DEFAULT_SERVICE_ACCOUNT,
                self.JSONPATH_METADATA_NAME,
                namespace=namespace,
            )
            return name.strip() == self.DEFAULT_SERVICE_ACCOUNT
        except Exception as read_error:  # noqa: BLE001 - absence is the expected early state, not a failure
            get_logger().log_info(f"'{self.DEFAULT_SERVICE_ACCOUNT}' ServiceAccount not readable in {namespace} yet: {read_error}")
            return False

    def _delete_namespace_and_confirm(self, namespace: str, phase: str) -> None:
        """Delete the scratch namespace and assert it is gone.

        Args:
            namespace (str): the namespace to remove.
            phase (str): the phase, for the failure message.

        Raises:
            KeywordException: when the namespace is still present after the timeout.
        """
        self.delete_namespace.delete_namespace(namespace)
        if not self.get_namespaces.wait_for_namespace_deleted(namespace, timeout=self.NAMESPACE_DELETE_TIMEOUT, interval=self.NAMESPACE_DELETE_INTERVAL):
            raise KeywordException(f"[{phase}] scratch namespace {namespace} was not removed; it is most likely stuck Terminating")

    def _discover_sleeper_image(self) -> str:
        """Find a usable probe image in the local registry and return a pullable reference.

        The image is discovered rather than pinned so the check survives a registry whose contents
        differ between labs. A bare repository name is not enough: the registry listing carries no
        tag and no host prefix, and a bare name resolves to an implicit :latest against a public
        registry, which fails to pull and looks exactly like the injection failure this check exists
        to detect.

        Returns:
            str: a fully qualified image reference, host and tag included.

        Raises:
            KeywordException: when the registry is unreachable, or holds no candidate image, or the
                chosen image has no tags.
        """
        if not self.registry_images.is_registry_reachable():
            raise KeywordException("the local registry is not reachable, so no probe image can be resolved")

        available = self.registry_images.get_registry_image_list().get_image_names()
        chosen = next((name for candidate in self.SLEEPER_IMAGE_PREFERENCE for name in available if candidate in name), None)
        if chosen is None:
            raise KeywordException(f"no probe image matching any of {self.SLEEPER_IMAGE_PREFERENCE} is present in the local registry. Found: {sorted(available)}")

        tags = self.registry_tags.get_image_tags(chosen).get_tag_names()
        if not tags:
            raise KeywordException(f"the local registry reports image {chosen} with no tags, so it cannot be pulled")

        registry_url = ConfigurationManager.get_docker_config().get_local_registry().get_registry_url()
        reference = f"{registry_url}/{chosen}:{tags[0]}"
        get_logger().log_info(f"probe image resolved to {reference} (tags available: {tags})")
        return reference

    def _ensure_pull_secret(self, namespace: str) -> None:
        """Create the registry pull secrets the probe pod needs, and confirm they exist.

        The scratch namespace is created by this check, so it carries no registry credential and the
        probe pod cannot pull without one. Secrets are created rather than copied from another
        namespace, so this does not depend on a resource some other test or person left behind.

        TWO secrets are needed, which is not obvious. The first is this check's own, named in the pod
        template. The second is the one istio's sidecar injector adds to the pod itself: observed on a
        26.03 AIO-SX, the injected pod reported "Unable to retrieve some image pull secrets
        (default-registry-key)" because the injector references that name and a fresh namespace does
        not have it. On that lab the proxyv2 image was already cached so it pulled anyway, which is
        exactly the kind of latent failure that would surface on a lab where it is not cached.

        The create verb does not assert its own result, so both secrets are read back. Asserting the
        operation rather than trusting it matters here because the failure mode - a pod that cannot
        pull - presents as a sidecar problem.

        Args:
            namespace (str): the namespace to create the secrets in.

        Raises:
            KeywordException: when a secret is not present after being created.
        """
        registry = ConfigurationManager.get_docker_config().get_local_registry()
        for secret_name in (self.PULL_SECRET_NAME, self.INJECTED_PULL_SECRET_NAME):
            self.create_secret.create_secret_for_registry(registry, secret_name, namespace=namespace)
        present = self.get_secrets.get_secret_names(namespace=namespace)
        for secret_name in (self.PULL_SECRET_NAME, self.INJECTED_PULL_SECRET_NAME):
            if secret_name not in present:
                raise KeywordException(f"registry pull secret {secret_name} was not created in namespace {namespace}, so the probe pod could not pull its image")

    def _render_pod(self, namespace: str, pod_name: str, sleep_image: str, phase: str) -> str:
        """Render the probe pod manifest for one phase.

        Args:
            namespace (str): the scratch namespace.
            pod_name (str): the pod name.
            sleep_image (str): the fully qualified probe image.
            phase (str): the phase, used to name the generated file.

        Returns:
            str: path on the controller to the rendered manifest.
        """
        return self.yaml.generate_yaml_file_from_template(
            get_stx_resource_path(self.POD_TEMPLATE),
            {
                "namespace": namespace,
                "test_pod_name": pod_name,
                "sleep_image": sleep_image,
                "pull_secret_name": self.PULL_SECRET_NAME,
            },
            f"{pod_name}.yaml",
            "/tmp",
        )

    def _container_names(self, namespace: str, pod_name: str) -> list[str]:
        """Return every container name in a pod, regular and init alike.

        Both lists are read because either can hold the sidecar, and which one does cannot be
        predicted from the istio version. Measured on hardware: the same istio 1.29.2 produced an
        init container on the 26.03 path and a regular container on the 25.09 path, so a single
        release ships both shapes depending on what the system was upgraded from.

        Args:
            namespace (str): the pod's namespace.
            pod_name (str): the pod name.

        Returns:
            list[str]: all container names found on the pod.
        """
        regular = self.resources.get_resource_field("pod", pod_name, self.JSONPATH_CONTAINERS, namespace=namespace)
        init = self.resources.get_resource_field("pod", pod_name, self.JSONPATH_INIT_CONTAINERS, namespace=namespace)
        return regular.split() + init.split()

    def _sidecar_is_present(self, namespace: str, pod_name: str) -> bool:
        """Report whether the istio sidecar was injected into a pod.

        Args:
            namespace (str): the pod's namespace.
            pod_name (str): the pod name.

        Returns:
            bool: True when istio-proxy is present as either a regular or an init container.
        """
        return self.SIDECAR_CONTAINER in self._container_names(namespace, pod_name)

    def _sidecar_image(self, namespace: str, pod_name: str) -> str:
        """Return the injected sidecar's image reference.

        Args:
            namespace (str): the pod's namespace.
            pod_name (str): the pod name.

        Returns:
            str: the sidecar image reference.

        Raises:
            KeywordException: when no istio-proxy image can be read from either container list.
        """
        for jsonpath in (self.JSONPATH_SIDECAR_IMAGE, self.JSONPATH_SIDECAR_IMAGE_INIT):
            image = self.resources.get_resource_field("pod", pod_name, jsonpath, namespace=namespace)
            if image:
                return image
        raise KeywordException(f"pod {pod_name} in {namespace} reports no {self.SIDECAR_CONTAINER} image in either its containers or its initContainers")

    def _validate_pod_is_ready(self, namespace: str, pod_name: str, phase: str, description: str) -> None:
        """Wait for a pod to report every one of its containers ready.

        The expectation is "all ready", not a literal count, because the count depends on where the
        sidecar landed AND on how the READY column is computed. Measured on a 26.03 AIO-SX
        running Kubernetes 1.34.8: an injected pod has one regular container and two init containers
        (istio-validation and istio-proxy) and reports READY as 2/2, not 1/1 - the restartable init
        container IS counted in the READY total. Deriving the expected count from the regular
        containers alone produced 1/1 and would have failed a healthy pod after a full timeout.

        Comparing ready against total sidesteps the question entirely and stays correct whichever
        way a future release counts.

        Args:
            namespace (str): the pod's namespace.
            pod_name (str): the pod name.
            phase (str): the phase, for the failure message.
            description (str): what this pod is, for the failure message.
        """
        validate_equals_with_retry(
            lambda: self._read_pod_all_containers_ready(namespace, pod_name),
            True,
            f"[{phase}] the {description} must become ready (all containers)",
            timeout=self.POD_READY_TIMEOUT,
            polling_sleep_time=self.POD_READY_POLL_INTERVAL,
        )

    def _read_pod_all_containers_ready(self, namespace: str, pod_name: str) -> bool:
        """Report whether a pod's READY column shows every container ready.

        Reads the "ready/total" string and compares the two halves, so no assumption is made about
        how many containers there should be. A total of zero is never treated as ready.

        This runs inside validate_equals_with_retry, which retries on a value and does not catch
        exceptions, so a read that raises would end the run with its timeout budget unspent. Around a
        deploy the platform restarts services and kubectl fails transiently, and the pod may not
        exist yet on the first poll, so both cases have to keep the wait going instead of ending it.

        Args:
            namespace (str): the pod's namespace.
            pod_name (str): the pod name.

        Returns:
            bool: True when the pod reports all of its containers ready.
        """
        ready_string = self._read_pod_ready(namespace, pod_name)
        if "/" not in ready_string:
            return False
        ready_count, _, total_count = ready_string.partition("/")
        if not ready_count.isdigit() or not total_count.isdigit() or int(total_count) == 0:
            return False
        return int(ready_count) == int(total_count)

    def _read_pod_ready(self, namespace: str, pod_name: str) -> str:
        """Read a pod's ready string, reporting a sentinel rather than raising.

        This runs inside validate_equals_with_retry, which retries on a value and does not catch
        exceptions, so a read that raises would end the run with its timeout budget unspent. Around
        a deploy the platform restarts services and kubectl fails transiently, and the pod may not
        exist yet on the first poll, so both cases have to keep the wait going instead of ending it.

        Args:
            namespace (str): the pod's namespace.
            pod_name (str): the pod name.

        Returns:
            str: the pod's ready string, or POD_STATE_UNREADABLE when it could not be read.
        """
        try:
            pods = self.pods.get_pods_with_retry(
                lambda: self.pods.get_pods(namespace),
                timeout=self.POD_READY_POLL_INTERVAL,
                poll_interval=self.POD_READY_POLL_INTERVAL,
            )
            return pods.get_pod(pod_name).get_ready()
        except Exception as read_error:  # noqa: BLE001 - a failed read must not end the wait
            get_logger().log_info(f"Could not read pod {pod_name} in {namespace} yet: {read_error}")
            return self.POD_STATE_UNREADABLE

    def _cleanup_finalizer(self, phase: str, namespace: str) -> Callable[[], None]:
        """Return a finalizer that removes the scratch namespace unless this phase already did.

        The finalizer is deliberately tolerant. It runs after a failure, where raising a
        housekeeping error would replace the real result with a misleading one.

        Args:
            phase (str): the phase the finalizer belongs to.
            namespace (str): the namespace to remove.

        Returns:
            Callable[[], None]: the finalizer to register.
        """

        def _finalizer() -> None:
            if phase not in self._cleaned_up_phases:
                self.delete_namespace.cleanup_namespace(namespace)

        return _finalizer

    def _mark_cleaned_up(self, phase: str) -> None:
        """Record that a phase removed its own artifacts, so its finalizer becomes a no-op.

        Args:
            phase (str): the phase that cleaned up.
        """
        self._cleaned_up_phases.add(phase)

    def _remove_generated_file(self, remote_path: str) -> None:
        """Delete a templated file this check wrote onto the system under test.

        Best effort: a leftover file is untidy but not a test failure, and reporting one would
        replace a real result with a housekeeping error.

        Args:
            remote_path (str): path on the controller to remove.
        """
        try:
            self.files.delete_file(remote_path)
        except Exception as delete_error:  # noqa: BLE001 - housekeeping must not fail the test
            get_logger().log_info(f"Could not remove {remote_path}: {delete_error}")

    def _apply_awaiting_webhook(self, resource_file: str, phase: str) -> None:
        """Apply a resource, waiting out an istio sidecar-injector webhook that is still starting.

        istio mutates pod creation through an admission webhook served by istiod under failurePolicy
        Fail. After a platform upgrade or rollback istiod is recreated, and there is a window in
        which it reports Running and Ready while the webhook is not yet answering. A create in that
        window says nothing about whether istio works, only that it was asked too early.

        Only the webhook-unavailable signatures are retried, so an istio that is broken in some other
        way is reported at once rather than after the full window. An istio that is permanently
        unreachable produces these same signatures, so that case is reported when the window expires
        instead of immediately - the trade for not failing a healthy system that was merely asked too
        early.

        Args:
            resource_file (str): path on the controller to the rendered resource file.
            phase (str): where in the upgrade this is running, for the failure message.

        Raises:
            KeywordException: when the webhook does not become available within the timeout.
        """
        deadline = time.time() + self.WEBHOOK_READY_TIMEOUT
        last_error = ""
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            output = self.file_apply.kubectl_apply_with_error(resource_file)
            if self.ssh_connection.get_return_code() == 0:
                if attempt > 1:
                    get_logger().log_info(f"[{phase}] istio sidecar-injector webhook became available on attempt {attempt}")
                return
            last_error = output
            # Compared case-insensitively. The markers are the lowercase forms, but kubectl relays
            # some of these verbatim from an HTTP layer that title-cases them - "Service
            # Unavailable" being the one that caught this out, so that marker could never match a
            # real 503 while it was compared as written.
            lowered_output = output.lower()
            if not any(marker.lower() in lowered_output for marker in self.WEBHOOK_UNAVAILABLE_MARKERS):
                # Not the webhook still starting up: report it now rather than retrying a real error.
                break
            get_logger().log_info(f"[{phase}] istio sidecar-injector webhook is not answering yet; retrying in {self.WEBHOOK_POLL_INTERVAL}s")
            time.sleep(self.WEBHOOK_POLL_INTERVAL)

        raise KeywordException(f"[{phase}] could not create the istio injection probe pod: {last_error}")
