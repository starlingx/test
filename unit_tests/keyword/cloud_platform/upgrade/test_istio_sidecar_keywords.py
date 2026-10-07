"""Unit tests for the istio sidecar-injection check.

These run against a stateful in-memory stand-in for the cluster rather than a sequence of canned
return values. That matters here: the check's correctness is mostly about ORDER - a pod created
before the namespace is labelled must come up without a sidecar, and the same pod created after must
come up with one - and a scripted list of return values would pass even if the keyword performed
those steps in the wrong order, or skipped the labelling entirely.

The model deliberately supports both sidecar layouts. istio made native sidecars the default in
1.27, but the layout is not decided by the version: the same istio 1.29.2 was measured as an init
container on the 26.03 upgrade path and a regular container on the 25.09 path, so the same check has
to work on both, and on the two-releases-back path it has to work across a transition between them
inside a single test run.

The real resource templates are rendered, so the manifests are covered too: a probe pod that lost
its imagePullSecrets is a pod that cannot pull, and the model reports it as never becoming ready.

No validate_* function is patched. Failures surface as the exceptions the production code would
really raise.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, NonCallableMagicMock, patch

import yaml
from jinja2 import Template

from keywords.cloud_platform.upgrade.istio_sidecar_keywords import IstioSidecarKeywords
from keywords.k8s.pods.object.kubectl_get_pods_output import KubectlGetPodsOutput

SIDECAR = "istio-proxy"
MULTUS_KEY = "k8s.v1.cni.cncf.io/networks"
SIDECAR_IMAGE = "registry.local:9001/docker.io/istio/proxyv2:1.29.2"
BASELINE_SIDECAR_IMAGE = "registry.local:9001/docker.io/istio/proxyv2:1.28.3"


def build_pods_output(pods: list[tuple[str, str, str]]) -> KubectlGetPodsOutput:
    """Return a KubectlGetPodsOutput built from simple pod tuples.

    The table parser locates each column by the character offset of its header, so values are padded
    to fixed widths to line up beneath it.

    Args:
        pods (list[tuple[str, str, str]]): tuples of (name, ready, status).

    Returns:
        KubectlGetPodsOutput: output object holding the described pods.
    """
    widths = (40, 10, 24, 12)
    columns = ("NAME", "READY", "STATUS", "RESTARTS")
    lines = ["".join(name.ljust(width) for name, width in zip(columns, widths)) + "AGE\n"]
    for name, ready, status in pods:
        values = (name, ready, status, "0")
        lines.append("".join(value.ljust(width) for value, width in zip(values, widths)) + "10m\n")
    return KubectlGetPodsOutput(lines, source="table")


class FakeCluster:
    """A small stateful stand-in for the cluster the keyword talks to.

    Holds namespaces and their labels, pods and their rendered specs, secrets, and the local
    registry's contents. Pod creation consults the namespace's labels at the moment of the create, so
    whether a sidecar is injected is a consequence of the keyword's ordering rather than something
    the test dictates.
    """

    def __init__(self, sidecar_position: str = "init", sidecar_image: str = SIDECAR_IMAGE, registry_images: list[str] = None, registry_tags: list[str] = None, apply_errors: list[str] = None, sa_delay_polls: int = 0, stuck_ready: str = None):
        """Build an empty cluster.

        Args:
            sidecar_position (str): "init" to inject istio-proxy as an init container or "regular"
                to inject it as a regular container. Both shapes were measured from the same istio
                1.29.2 on different upgrade paths, so this is not a proxy-version switch.
            sidecar_image (str): the image the injected sidecar runs.
            registry_images (list[str]): image names the local registry reports. Defaults to busybox.
            registry_tags (list[str]): tags the local registry reports for the chosen image.
            apply_errors (list[str]): error strings that the webhook-aware apply emits, in order,
                before eventually succeeding.
            sa_delay_polls (int): how many reads of a new namespace's 'default' ServiceAccount fail
                before it appears, modelling the asynchronous service-account controller. 0 means
                it exists as soon as the namespace does.
            stuck_ready (str): when set, every injected pod reports this ready string forever,
                modelling a pod that comes up but never becomes ready.
        """
        self.namespaces = {}
        self.pods = {}
        self.secrets = {}
        self.nads = set()
        self.rendered = {}
        self.rendered_images = []
        self.sidecar_position = sidecar_position
        self.sidecar_image = sidecar_image
        self.registry_images = ["docker.io/library/busybox"] if registry_images is None else registry_images
        self.registry_tags = ["1.37"] if registry_tags is None else registry_tags
        self.registry_reachable = True
        self.apply_errors = [] if apply_errors is None else list(apply_errors)
        self.return_code = 0
        self.deleted_namespaces = []
        self.labelled_namespaces = []
        self.service_accounts = set()
        self.sa_delay_polls = sa_delay_polls
        self._sa_reads_remaining = {}
        self.pods_rejected_for_missing_sa = []
        # Where the injector put the sidecar, recorded per injected pod, so a test can assert the
        # model really produced the layout it was configured for. Without this the layout tests
        # pass even if the model ignores sidecar_position, which makes them prove nothing.
        self.stuck_ready = stuck_ready
        self.injection_shapes = []
        # Every ready string this model reported, so FACT 1 (an injected pod reads 2/2, not 1/1)
        # can be pinned against the model rather than only against a stubbed reader.
        self.reported_ready = []

    # --- namespaces -------------------------------------------------------------------------

    def create_namespaces(self, name: str) -> None:
        """Create a namespace, failing if it already exists, as the real asserting verb does.

        Args:
            name (str): namespace name.

        Raises:
            AssertionError: when the namespace already exists.
        """
        if name in self.namespaces:
            raise AssertionError(f"namespace {name} already exists")
        self.namespaces[name] = {"labels": {}}
        if self.sa_delay_polls <= 0:
            self.service_accounts.add(name)
        else:
            self._sa_reads_remaining[name] = self.sa_delay_polls

    def cleanup_namespace(self, name: str) -> int:
        """Delete a namespace tolerantly, reporting a non-zero code when it was absent.

        Args:
            name (str): namespace name.

        Returns:
            int: 0 when a namespace was removed, 1 when there was nothing to remove.
        """
        if name in self.namespaces:
            self._drop_namespace(name)
            return 0
        return 1

    def delete_namespace(self, name: str) -> str:
        """Delete a namespace, failing if it was absent, as the real asserting verb does.

        Args:
            name (str): namespace name.

        Returns:
            str: the command output.

        Raises:
            AssertionError: when the namespace does not exist.
        """
        if name not in self.namespaces:
            raise AssertionError(f"namespace {name} does not exist")
        self._drop_namespace(name)
        return ""

    def _drop_namespace(self, name: str) -> None:
        """Remove a namespace and everything scoped to it.

        Args:
            name (str): namespace name.
        """
        del self.namespaces[name]
        self.deleted_namespaces.append(name)
        for key in [key for key in self.pods if key[0] == name]:
            del self.pods[key]
        self.nads = {nad for nad in self.nads if nad[0] != name}
        self.secrets.pop(name, None)

    def wait_for_namespace_deleted(self, namespace: str, timeout: int = 300, interval: int = 60) -> bool:
        """Report whether a namespace is absent.

        Args:
            namespace (str): namespace name.
            timeout (int): ignored; the model is synchronous.
            interval (int): ignored; the model is synchronous.

        Returns:
            bool: True when the namespace does not exist.
        """
        return namespace not in self.namespaces

    def label_namespace(self, namespace: str, key: str, value: str) -> None:
        """Set a label on a namespace.

        Args:
            namespace (str): namespace name.
            key (str): label key.
            value (str): label value.

        Raises:
            AssertionError: when the namespace does not exist.
        """
        if namespace not in self.namespaces:
            raise AssertionError(f"cannot label missing namespace {namespace}")
        self.namespaces[namespace]["labels"][key] = value
        self.labelled_namespaces.append(namespace)

    # --- templating and apply ---------------------------------------------------------------

    def generate_yaml_file_from_template(self, template_file: str, replacements: dict, target_file_name: str, target_remote_location: str) -> str:
        """Render a real template file and remember the result against its path.

        Args:
            template_file (str): absolute path to the template.
            replacements (dict): substitutions.
            target_file_name (str): rendered file name.
            target_remote_location (str): remote directory.

        Returns:
            str: the path the rendered file would occupy.
        """
        with open(template_file) as handle:
            document = yaml.safe_load(Template(handle.read()).render(replacements))
        path = f"{target_remote_location}/{target_file_name}"
        self.rendered[path] = document
        if document["kind"] == "Pod":
            self.rendered_images.append(document["spec"]["containers"][0]["image"])
        return path

    def apply_resource_from_yaml(self, yaml_file: str, validate: bool = True) -> None:
        """Apply a rendered resource, asserting success as the real verb does.

        Args:
            yaml_file (str): path to the rendered file.
            validate (bool): ignored; present to match the real signature.
        """
        document = self.rendered.get(yaml_file, {})
        if document.get("kind") == "Pod":
            namespace = document["metadata"]["namespace"]
            if namespace not in self.service_accounts:
                self.pods_rejected_for_missing_sa.append(yaml_file)
                raise AssertionError(f'pods is forbidden: error looking up service account {namespace}/default: serviceaccount "default" not found')
        self._materialize(yaml_file)
        self.return_code = 0

    def kubectl_apply_with_error(self, yaml_file: str) -> str:
        """Apply a rendered resource, returning an error string instead of raising.

        Args:
            yaml_file (str): path to the rendered file.

        Returns:
            str: empty on success, or the next scripted error.
        """
        if self.apply_errors:
            self.return_code = 1
            return self.apply_errors.pop(0)
        self._materialize(yaml_file)
        self.return_code = 0
        return ""

    def get_return_code(self) -> int:
        """Report the return code of the last apply.

        Returns:
            int: the last return code.
        """
        return self.return_code

    def _materialize(self, path: str) -> None:
        """Turn a rendered document into cluster state.

        A Pod consults its namespace's labels at this moment, so injection is a consequence of when
        the keyword created it. A pod whose pull secret is missing from the namespace is recorded as
        unpullable and never becomes ready, which is what a real ImagePullBackOff would do.

        Args:
            path (str): path of the rendered file.

        Raises:
            AssertionError: when the target namespace does not exist.
        """
        document = self.rendered[path]
        namespace = document["metadata"]["namespace"]
        if namespace not in self.namespaces:
            raise AssertionError(f"cannot apply into missing namespace {namespace}")

        if document["kind"] == "NetworkAttachmentDefinition":
            self.nads.add((namespace, document["metadata"]["name"]))
            return

        containers = [container["name"] for container in document["spec"]["containers"]]
        init_containers = []
        annotations = dict(document["metadata"].get("annotations") or {})
        requested_secrets = [secret["name"] for secret in document["spec"].get("imagePullSecrets") or []]
        pullable = bool(requested_secrets) and all(secret in self.secrets.get(namespace, set()) for secret in requested_secrets)

        if self.namespaces[namespace]["labels"].get("istio-injection") == "enabled":
            if self.sidecar_position == "init":
                # Real injection adds istio-validation alongside istio-proxy, observed on a lab.
                init_containers.extend(["istio-validation", SIDECAR])
                self.injection_shapes.append("initContainers")
            else:
                containers.append(SIDECAR)
                self.injection_shapes.append("containers")
            annotations[MULTUS_KEY] = "istio-cni"
            # The injector also references its own pull secret; without it in the namespace the
            # kubelet cannot retrieve it.
            requested_secrets.append("default-registry-key")
            pullable = all(secret in self.secrets.get(namespace, set()) for secret in requested_secrets)

        self.pods[(namespace, document["metadata"]["name"])] = {
            "containers": containers,
            "initContainers": init_containers,
            "annotations": annotations,
            "pullable": pullable,
        }

    # --- reads ------------------------------------------------------------------------------

    def get_resource_field(self, resource_type: str, resource_name: str, jsonpath: str, namespace: str = None) -> str:
        """Answer the jsonpath reads the keyword makes.

        Args:
            resource_type (str): the resource kind.
            resource_name (str): the resource name.
            jsonpath (str): the jsonpath expression.
            namespace (str): the namespace.

        Returns:
            str: the field value, empty when absent, as kubectl reports a missing key.

        Raises:
            AssertionError: when the pod does not exist.
            ValueError: when the test model is asked for a jsonpath it does not implement.
        """
        if resource_type == "serviceaccount":
            if namespace in self.service_accounts and resource_name == "default":
                return "default"
            remaining = self._sa_reads_remaining.get(namespace, 0)
            if remaining > 0:
                self._sa_reads_remaining[namespace] = remaining - 1
                if self._sa_reads_remaining[namespace] == 0:
                    self.service_accounts.add(namespace)
            raise AssertionError(f'serviceaccount "{resource_name}" not found in {namespace}')

        pod = self.pods.get((namespace, resource_name))
        if pod is None:
            raise AssertionError(f"pod {resource_name} not found in {namespace}")

        if jsonpath == IstioSidecarKeywords.JSONPATH_CONTAINERS:
            return " ".join(pod["containers"])
        if jsonpath == IstioSidecarKeywords.JSONPATH_INIT_CONTAINERS:
            return " ".join(pod["initContainers"])
        if jsonpath == IstioSidecarKeywords.JSONPATH_SIDECAR_IMAGE:
            return self.sidecar_image if SIDECAR in pod["containers"] else ""
        if jsonpath == IstioSidecarKeywords.JSONPATH_SIDECAR_IMAGE_INIT:
            return self.sidecar_image if SIDECAR in pod["initContainers"] else ""
        if jsonpath == IstioSidecarKeywords.JSONPATH_MULTUS_ANNOTATION:
            return pod["annotations"].get(MULTUS_KEY, "")
        raise ValueError(f"the cluster model does not implement jsonpath {jsonpath}")

    def get_pods(self, namespace: str = None, label: str = None) -> KubectlGetPodsOutput:
        """Return the pods in a namespace as the real output object.

        Args:
            namespace (str): the namespace to list.
            label (str): ignored.

        Returns:
            KubectlGetPodsOutput: the pods in that namespace.
        """
        rows = []
        for (pod_namespace, name), pod in self.pods.items():
            if pod_namespace != namespace:
                continue
            # Kubernetes counts restartable init containers (native sidecars) in the READY
            # total. Measured on a 26.03 AIO-SX / k8s 1.34.8: one regular container plus an
            # injected init sidecar reports 2/2, not 1/1.
            total = len(pod["containers"]) + len([c for c in pod["initContainers"] if c == SIDECAR])
            if self.stuck_ready is not None and SIDECAR in pod["containers"] + pod["initContainers"]:
                ready = self.stuck_ready
            elif pod["pullable"]:
                ready = f"{total}/{total}"
            else:
                ready = f"0/{total}"
            if (namespace, name) not in [(n, p) for n, p, _ in self.reported_ready]:
                self.reported_ready.append((namespace, name, ready))
            rows.append((name, ready, "Running" if pod["pullable"] else "ImagePullBackOff"))
        return build_pods_output(rows)

    def get_pods_with_retry(self, reader: object, timeout: int = 60, poll_interval: int = 10) -> KubectlGetPodsOutput:
        """Call the reader once; the model has no transient failures unless a test adds them.

        Args:
            reader (object): the callable producing the pod output.
            timeout (int): ignored.
            poll_interval (int): ignored.

        Returns:
            KubectlGetPodsOutput: whatever the reader produced.
        """
        return reader()

    # --- secrets and registry ---------------------------------------------------------------

    def create_secret_for_registry(self, registry: object, secret_name: str, namespace: str = "default") -> None:
        """Create a registry pull secret. Deliberately does not assert, matching the real verb.

        Args:
            registry (object): the registry object.
            secret_name (str): the secret name.
            namespace (str): the namespace.
        """
        self.secrets.setdefault(namespace, set()).add(secret_name)

    def get_secret_names(self, namespace: str = "default") -> list[str]:
        """List secret names in a namespace.

        Args:
            namespace (str): the namespace.

        Returns:
            list[str]: the secret names.
        """
        return sorted(self.secrets.get(namespace, set()))

    def is_registry_reachable(self, command_timeout: int = 120) -> bool:
        """Report whether the local registry answers.

        Args:
            command_timeout (int): ignored.

        Returns:
            bool: the configured reachability.
        """
        return self.registry_reachable

    def get_registry_image_list(self, command_timeout: int = 120) -> NonCallableMagicMock:
        """Return an object exposing the registry's image names.

        Args:
            command_timeout (int): ignored.

        Returns:
            NonCallableMagicMock: object whose get_image_names returns the configured names.
        """
        output = NonCallableMagicMock()
        output.get_image_names = MagicMock(return_value=list(self.registry_images))
        return output

    def get_image_tags(self, image_name: str, command_timeout: int = 60) -> NonCallableMagicMock:
        """Return an object exposing the tags of an image.

        Args:
            image_name (str): the image queried.
            command_timeout (int): ignored.

        Returns:
            NonCallableMagicMock: object whose get_tag_names returns the configured tags.
        """
        output = NonCallableMagicMock()
        output.get_tag_names = MagicMock(return_value=list(self.registry_tags))
        return output

    def delete_file(self, file_name: str) -> bool:
        """Forget a rendered file.

        Args:
            file_name (str): the path to forget.

        Returns:
            bool: always True.
        """
        self.rendered.pop(file_name, None)
        return True


class IstioSidecarKeywordsTestBase(unittest.TestCase):
    """Shared wiring for the sidecar-check tests."""

    def setUp(self):
        """Silence loggers and shorten every wait so the suite runs without sleeping."""
        self.patchers = [
            patch("keywords.base_keyword.get_logger"),
            patch("keywords.cloud_platform.upgrade.istio_sidecar_keywords.get_logger"),
            patch("framework.validation.validation.get_logger"),
            patch.object(IstioSidecarKeywords, "POD_READY_TIMEOUT", 1),
            patch.object(IstioSidecarKeywords, "POD_READY_POLL_INTERVAL", 1),
            patch.object(IstioSidecarKeywords, "NAMESPACE_DELETE_TIMEOUT", 1),
            patch.object(IstioSidecarKeywords, "NAMESPACE_DELETE_INTERVAL", 1),
            patch.object(IstioSidecarKeywords, "WEBHOOK_READY_TIMEOUT", 2),
            patch.object(IstioSidecarKeywords, "WEBHOOK_POLL_INTERVAL", 0),
            patch.object(IstioSidecarKeywords, "SERVICE_ACCOUNT_TIMEOUT", 2),
            patch.object(IstioSidecarKeywords, "SERVICE_ACCOUNT_POLL_INTERVAL", 0),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.addCleanup(self._stop_patchers)

    def _stop_patchers(self):
        """Stop every patcher."""
        for patcher in self.patchers:
            patcher.stop()

    def build(self, cluster: FakeCluster) -> IstioSidecarKeywords:
        """Return a keyword instance wired to a cluster model.

        BaseKeyword.__getattribute__ wraps callable attributes in a logging wrapper, so collaborators
        are installed with object.__setattr__ and built from NonCallableMagicMock.

        Args:
            cluster (FakeCluster): the cluster model to wire in.

        Returns:
            IstioSidecarKeywords: instance backed by that model.
        """
        keywords = IstioSidecarKeywords.__new__(IstioSidecarKeywords)

        def stub(**methods: object) -> NonCallableMagicMock:
            """Build a non-callable mock exposing the given bound methods.

            Args:
                **methods (object): attribute name to callable.

            Returns:
                NonCallableMagicMock: the collaborator stub.
            """
            collaborator = NonCallableMagicMock()
            for name, function in methods.items():
                setattr(collaborator, name, MagicMock(side_effect=function))
            return collaborator

        object.__setattr__(keywords, "ssh_connection", stub(get_return_code=cluster.get_return_code))
        object.__setattr__(keywords, "create_namespace", stub(create_namespaces=cluster.create_namespaces))
        object.__setattr__(keywords, "delete_namespace", stub(cleanup_namespace=cluster.cleanup_namespace, delete_namespace=cluster.delete_namespace))
        object.__setattr__(keywords, "get_namespaces", stub(wait_for_namespace_deleted=cluster.wait_for_namespace_deleted))
        object.__setattr__(keywords, "label_namespace", stub(label_namespace=cluster.label_namespace))
        object.__setattr__(keywords, "yaml", stub(generate_yaml_file_from_template=cluster.generate_yaml_file_from_template))
        object.__setattr__(keywords, "file_apply", stub(apply_resource_from_yaml=cluster.apply_resource_from_yaml, kubectl_apply_with_error=cluster.kubectl_apply_with_error))
        object.__setattr__(keywords, "files", stub(delete_file=cluster.delete_file))
        object.__setattr__(keywords, "resources", stub(get_resource_field=cluster.get_resource_field))
        object.__setattr__(keywords, "pods", stub(get_pods=cluster.get_pods, get_pods_with_retry=cluster.get_pods_with_retry))
        object.__setattr__(keywords, "create_secret", stub(create_secret_for_registry=cluster.create_secret_for_registry))
        object.__setattr__(keywords, "get_secrets", stub(get_secret_names=cluster.get_secret_names))
        object.__setattr__(keywords, "registry_images", stub(is_registry_reachable=cluster.is_registry_reachable, get_registry_image_list=cluster.get_registry_image_list))
        object.__setattr__(keywords, "registry_tags", stub(get_image_tags=cluster.get_image_tags))
        object.__setattr__(keywords, "_cleaned_up_phases", set())
        return keywords

    @staticmethod
    def request_stub() -> NonCallableMagicMock:
        """Return a pytest request stub that records finalizers.

        Returns:
            NonCallableMagicMock: stub exposing addfinalizer.
        """
        request = NonCallableMagicMock()
        request.finalizers = []
        request.addfinalizer = MagicMock(side_effect=request.finalizers.append)
        return request

    def run_check(self, cluster: FakeCluster, phase: str = "pre") -> str:
        """Run the sidecar check against a cluster model.

        Args:
            cluster (FakeCluster): the cluster model.
            phase (str): the phase name.

        Returns:
            str: the sidecar image tag the check reports.
        """
        keywords = self.build(cluster)
        with patch("keywords.cloud_platform.upgrade.istio_sidecar_keywords.ConfigurationManager") as config:
            config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = "registry.local:9001"
            return keywords.validate_sidecar_is_injected(self.request_stub(), phase)


class TestSidecarInjectionPasses(IstioSidecarKeywordsTestBase):
    """The check passes on a healthy cluster, in both sidecar layouts."""

    def test_native_sidecar_layout_passes_and_returns_the_tag(self):
        """The native layout puts istio-proxy in initContainers; the check must accept it and read the tag."""
        cluster = FakeCluster(sidecar_position="init")
        self.assertEqual(self.run_check(cluster), "1.29.2")

    def test_classic_sidecar_layout_passes_and_returns_the_tag(self):
        """The classic layout puts istio-proxy in containers; the same check must accept that too."""
        cluster = FakeCluster(sidecar_position="regular")
        self.assertEqual(self.run_check(cluster), "1.29.2")

    def test_readiness_compares_ready_against_total_not_a_derived_count(self):
        """An injected pod reports 2/2 even though it has only one regular container.

        Measured on a 26.03 AIO-SX running Kubernetes 1.34.8: the restartable init container IS
        counted in the READY total. An earlier version derived the expected count from the regular
        containers alone, computed 1/1, and would have failed a healthy pod after a full timeout.
        Comparing ready against total is correct whichever way the kubelet counts.
        """
        keywords = self.build(FakeCluster())
        for ready_string, expected in [("2/2", True), ("1/1", True), ("3/3", True), ("1/2", False), ("0/1", False), ("0/0", False)]:
            with self.subTest(ready=ready_string):
                object.__setattr__(keywords, "_read_pod_ready", lambda ns, pod, r=ready_string: r)
                self.assertEqual(keywords._read_pod_all_containers_ready("ns", "pod"), expected)

    def test_the_phase_survives_a_slow_default_service_account(self):
        """A namespace's 'default' ServiceAccount is created asynchronously; the check must wait.

        Observed on a 25.09 AIO-SX post-upgrade: applying the probe pod immediately after creating
        the namespace was rejected outright with

            pods "..." is forbidden: error looking up service account <ns>/default:
            serviceaccount "default" not found

        That is an admission error, not a pod condition, so no amount of pod-readiness retrying
        recovers from it. With the wait in place the phase must succeed even when the controller
        takes several polls.
        """
        cluster = FakeCluster(sa_delay_polls=3)
        self.assertEqual(self.run_check(cluster), "1.29.2")
        self.assertEqual(cluster.pods_rejected_for_missing_sa, [], "no pod should have been applied before the ServiceAccount existed")

    def test_a_pod_applied_before_the_service_account_is_rejected(self):
        """Guards the fidelity of the model above.

        If the fake cluster accepted a pod in a namespace with no 'default' ServiceAccount, the
        preceding test would pass whether or not the keyword actually waits. This asserts the model
        rejects it, so that test has something real to prove.
        """
        cluster = FakeCluster(sa_delay_polls=1)
        cluster.create_namespaces("stxtest-istio-pre")
        cluster.rendered["/tmp/p.yaml"] = {"kind": "Pod", "metadata": {"name": "p", "namespace": "stxtest-istio-pre"}, "spec": {"containers": [{"image": "img"}]}}
        with self.assertRaises(AssertionError) as caught:
            cluster.apply_resource_from_yaml("/tmp/p.yaml")
        self.assertIn("serviceaccount", str(caught.exception).lower())

    def test_a_service_account_that_never_appears_fails_with_a_clear_message(self):
        """A ServiceAccount that never arrives must fail naming what was waited for."""
        cluster = FakeCluster(sa_delay_polls=10**6)
        with self.assertRaises(Exception) as caught:
            self.run_check(cluster)
        self.assertIn("ServiceAccount", str(caught.exception))

    def test_the_service_account_reader_reports_absence_rather_than_raising(self):
        """The reader runs inside a value-retry, so it must absorb the read error.

        validate_equals_with_retry retries on a value and does not catch exceptions. A missing
        ServiceAccount makes the underlying read assert, so if that propagated the wait would end
        on the very condition it exists to wait out.
        """
        cluster = FakeCluster()
        keywords = self.build(cluster)
        self.assertFalse(keywords._read_default_service_account_exists("no-such-namespace"))
        cluster.create_namespaces("has-one")
        self.assertTrue(keywords._read_default_service_account_exists("has-one"))

    def test_a_pod_with_zero_containers_is_never_ready(self):
        """A total of zero must not read as all-ready."""
        keywords = self.build(FakeCluster())
        object.__setattr__(keywords, "_read_pod_ready", lambda ns, pod: "0/0")
        self.assertFalse(keywords._read_pod_all_containers_ready("ns", "pod"))

    def test_an_unreadable_pod_is_never_ready(self):
        """The sentinel must not be mistaken for a ready pod."""
        keywords = self.build(FakeCluster())
        object.__setattr__(keywords, "_read_pod_ready", lambda ns, pod: IstioSidecarKeywords.POD_STATE_UNREADABLE)
        self.assertFalse(keywords._read_pod_all_containers_ready("ns", "pod"))

    def test_the_injector_pull_secret_is_provisioned(self):
        """istio's injector references default-registry-key, so the scratch namespace needs it."""
        cluster = FakeCluster()
        created = []
        original = cluster.create_secret_for_registry

        def record(registry: object, secret_name: str, namespace: str = "default") -> None:
            """Record each secret created.

            Args:
                registry (object): the registry object.
                secret_name (str): the secret name.
                namespace (str): the namespace.
            """
            created.append(secret_name)
            original(registry, secret_name, namespace=namespace)

        cluster.create_secret_for_registry = record
        self.run_check(cluster)
        self.assertIn(IstioSidecarKeywords.PULL_SECRET_NAME, created)
        self.assertIn(IstioSidecarKeywords.INJECTED_PULL_SECRET_NAME, created)

    def test_a_namespace_is_not_leaked_when_preparing_it_fails(self):
        """The cleanup finalizer must be registered before the namespace is created, not after.

        Preparing the namespace includes waiting for its ServiceAccount, which can time out. With
        the finalizer registered afterwards, that timeout left a created namespace behind with
        nothing to remove it, which poisons every later run on the same lab - the very failure the
        pre-clean step exists to recover from.
        """
        cluster = FakeCluster(sa_delay_polls=10**6)
        finalizers = []
        request = SimpleNamespace(addfinalizer=finalizers.append)
        keywords = self.build(cluster)
        with self.assertRaises(Exception):
            keywords.validate_sidecar_is_injected(request, "pre")
        self.assertTrue(finalizers, "a finalizer must have been registered before the failure")
        self.assertIn("stxtest-istio-pre", cluster.namespaces, "the namespace was created, so it needs cleaning")
        for finalizer in finalizers:
            finalizer()
        self.assertNotIn("stxtest-istio-pre", cluster.namespaces, "the finalizer must have removed it")

    def test_an_injected_pod_that_never_becomes_ready_fails_the_phase(self):
        """Readiness must be asserted, not merely read.

        Both readiness waits could be deleted and every other test still passed, because they all
        assert the returned tag and an unready pod still has a readable image. A sidecar that is
        injected but never ready is precisely the regression this check exists to catch.
        """
        cluster = FakeCluster(stuck_ready="1/2")
        with self.assertRaises(Exception) as caught:
            self.run_check(cluster, "pre")
        self.assertIn("ready", str(caught.exception).lower())

    def test_a_sidecar_whose_image_is_not_proxyv2_fails_the_phase(self):
        """The image assertion must be asserted too.

        A container called istio-proxy running something other than the proxy would satisfy every
        other assertion in the phase. Removing the proxyv2 check left the whole suite green.
        """
        cluster = FakeCluster(sidecar_image="registry.local:9001/docker.io/istio/pilot:1.29.2")
        # validate_str_contains puts its description in the log rather than the exception, so the
        # assertion here is that the phase fails at all - with the marker removed it returns a tag
        # and passes, which is the regression being pinned.
        with self.assertRaises(Exception):
            self.run_check(cluster, "pre")

    def test_the_two_layouts_are_genuinely_different_shapes(self):
        """Guard the model itself: the two positions must produce different pod specs.

        This previously asserted that the rendered-file bookkeeping was empty, which is cleanup
        and says nothing about layout. Because the check unions both container lists it returns the
        same tag either way, so asserting only its return value cannot tell a model that honours
        sidecar_position from one that ignores it - and a model that always injected an init
        sidecar passed all of these tests.

        Asserting where the injector actually put the sidecar makes the model's fidelity
        load-bearing, which is what the two layout tests above depend on.
        """
        native = FakeCluster(sidecar_position="init")
        self.run_check(native, "pre")
        classic = FakeCluster(sidecar_position="regular")
        self.run_check(classic, "pre")
        self.assertEqual(native.injection_shapes, ["initContainers"], "the native model must inject an init sidecar")
        self.assertEqual(classic.injection_shapes, ["containers"], "the classic model must inject a regular sidecar")
        self.assertNotEqual(native.injection_shapes, classic.injection_shapes)

    def test_an_injected_pod_reads_two_of_two_in_both_layouts(self):
        """FACT 1, pinned against the model: one workload container plus a sidecar reads 2/2.

        Measured on a 26.03 AIO-SX running Kubernetes 1.34.8. It holds for both layouts but for
        different reasons - the restartable init container is counted in the native case, and there
        are simply two regular containers in the classic case. A derived expectation of 1/1 fails
        both, which is why the check compares ready against total instead.
        """
        for position in ("init", "regular"):
            with self.subTest(position=position):
                cluster = FakeCluster(sidecar_position=position)
                self.run_check(cluster, "pre")
                injected = [ready for _, pod, ready in cluster.reported_ready if "injected" in pod]
                self.assertIn("2/2", injected, f"an injected pod must read 2/2 in the {position} layout")
                unlabelled = [ready for _, pod, ready in cluster.reported_ready if "unlabelled" in pod]
                self.assertIn("1/1", unlabelled, "the uninjected control must read 1/1")

    def test_webhook_markers_match_regardless_of_case(self):
        """A 503 relayed by kubectl reads "Service Unavailable", not "service unavailable".

        The marker list is written in lowercase and was compared as written, so the one marker
        whose real text is title-cased by the HTTP layer could never fire. Comparing case
        insensitively fixes that and stops the same trap catching a future marker.
        """
        for text in ("Error from server: Service Unavailable", 'failed calling webhook "x"', "net/http: TLS handshake timeout: EOF"):
            with self.subTest(text=text):
                cluster = FakeCluster(apply_errors=[text])
                # The retry treats this as the webhook still starting, so the phase still succeeds.
                self.assertEqual(self.run_check(cluster, "pre"), "1.29.2")

    def test_a_layout_change_between_phases_is_tolerated(self):
        """A single keyword instance must cope with a different layout in a later phase.

        This is a robustness property, not an observed one, and the distinction matters. Both
        upgrade paths measured on hardware were internally consistent: every phase of the
        one-release-back run saw an init container, and every phase of the two-releases-back run saw
        a regular container. Neither changed shape part-way through.

        It is still worth pinning, because the layout comes from the injector configuration carried
        through the upgrade rather than from the proxy version, so nothing guarantees a run stays
        consistent. An earlier version of this test asserted that the two-releases-back path DOES
        change shape mid-run and justified it by 25.09 predating native sidecars - both the claim
        and its reasoning were wrong, and the reasoning was the very version-based model the rest of
        this change exists to refute.
        """
        baseline_cluster = FakeCluster(sidecar_position="regular", sidecar_image=BASELINE_SIDECAR_IMAGE)
        baseline = self.run_check(baseline_cluster, "pre")

        upgraded_cluster = FakeCluster(sidecar_position="init", sidecar_image=SIDECAR_IMAGE)
        upgraded = self.run_check(upgraded_cluster, "post-upgrade")

        self.assertEqual(baseline, "1.28.3")
        self.assertEqual(upgraded, "1.29.2")
        self.assertNotEqual(baseline, upgraded)
        # The tags above differ because the two models were given different images, so on their own
        # they say nothing about layout. These assert the shapes really did differ between the
        # phases, which is the property being covered.
        self.assertEqual(baseline_cluster.injection_shapes, ["containers"])
        self.assertEqual(upgraded_cluster.injection_shapes, ["initContainers"])


class TestOrderingIsEnforced(IstioSidecarKeywordsTestBase):
    """The check's ordering guarantees."""

    def test_the_namespace_is_labelled_before_the_injected_pod_is_created(self):
        """The label must be set between the two pods, or the negative control is meaningless."""
        cluster = FakeCluster()
        self.run_check(cluster)
        self.assertEqual(cluster.labelled_namespaces, ["stxtest-istio-pre"])

    def test_the_nad_is_created_in_the_scratch_namespace(self):
        """The Multus NAD must exist in the pod's own namespace or an injected pod never leaves Init."""
        cluster = FakeCluster()
        keywords = self.build(cluster)
        observed = {}

        original = cluster.label_namespace

        def record_then_label(namespace: str, key: str, value: str) -> None:
            """Capture the NADs present at the moment the namespace is labelled.

            Args:
                namespace (str): namespace name.
                key (str): label key.
                value (str): label value.
            """
            observed["nads"] = set(cluster.nads)
            original(namespace, key, value)

        cluster.label_namespace = record_then_label
        object.__setattr__(keywords, "label_namespace", NonCallableMagicMock(label_namespace=MagicMock(side_effect=record_then_label)))
        with patch("keywords.cloud_platform.upgrade.istio_sidecar_keywords.ConfigurationManager") as config:
            config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = "registry.local:9001"
            keywords.validate_sidecar_is_injected(self.request_stub(), "pre")
        self.assertEqual(observed["nads"], {("stxtest-istio-pre", "istio-cni")})

    def test_a_leftover_namespace_is_cleared_before_the_run(self):
        """A namespace left by an interrupted run must not make the next run fail on create."""
        cluster = FakeCluster()
        cluster.namespaces["stxtest-istio-pre"] = {"labels": {"istio-injection": "enabled"}}
        self.assertEqual(self.run_check(cluster), "1.29.2")

    def test_the_namespace_is_deleted_at_the_end_of_the_phase(self):
        """Artifacts are removed by the phase that made them, not left to teardown."""
        cluster = FakeCluster()
        self.run_check(cluster)
        self.assertNotIn("stxtest-istio-pre", cluster.namespaces)
        self.assertIn("stxtest-istio-pre", cluster.deleted_namespaces)

    def test_each_phase_uses_its_own_namespace(self):
        """Phases must not share a namespace, because the injection label lives on it."""
        cluster = FakeCluster()
        self.run_check(cluster, "pre")
        self.run_check(cluster, "post-upgrade")
        self.assertEqual(sorted(set(cluster.deleted_namespaces)), ["stxtest-istio-post-upgrade", "stxtest-istio-pre"])


class TestFailuresAreDetected(IstioSidecarKeywordsTestBase):
    """Conditions the check must refuse to pass."""

    def test_injection_not_happening_fails(self):
        """A cluster whose injector does nothing must fail, not pass quietly."""
        cluster = FakeCluster()
        keywords = self.build(cluster)
        # An injector that never adds a sidecar: labelling has no effect.
        object.__setattr__(keywords, "label_namespace", NonCallableMagicMock(label_namespace=MagicMock()))
        with patch("keywords.cloud_platform.upgrade.istio_sidecar_keywords.ConfigurationManager") as config:
            config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = "registry.local:9001"
            with self.assertRaises(Exception):
                keywords.validate_sidecar_is_injected(self.request_stub(), "pre")

    def test_a_missing_multus_annotation_fails(self):
        """The annotation's absence is a real regression, not an environment quirk.

        It is not incidental and it is not platform-specific: app-istio configures the injector to
        add it, in stx-istio-helm's istio-pilot static overrides
        (k8s.v1.cni.cncf.io/networks: istio-cni). So an injected pod without it means the injector
        is no longer applying that configuration, which is exactly what this check exists to catch.
        """
        cluster = FakeCluster()
        original = cluster._materialize

        def materialize_without_annotation(path: str) -> None:
            """Materialize a pod then strip its Multus annotation.

            Args:
                path (str): rendered file path.
            """
            original(path)
            document = cluster.rendered[path]
            if document["kind"] == "Pod":
                cluster.pods[(document["metadata"]["namespace"], document["metadata"]["name"])]["annotations"].pop(MULTUS_KEY, None)

        cluster._materialize = materialize_without_annotation
        with self.assertRaises(Exception):
            self.run_check(cluster)

    def test_an_unreachable_registry_fails_as_itself(self):
        """An unreachable registry must be reported as that, not as a pull or injection failure."""
        cluster = FakeCluster()
        cluster.registry_reachable = False
        with self.assertRaises(Exception) as caught:
            self.run_check(cluster)
        self.assertIn("registry", str(caught.exception).lower())

    def test_no_candidate_image_fails_and_names_what_was_found(self):
        """A registry with nothing usable must say what it did hold, so the run diagnoses itself."""
        cluster = FakeCluster(registry_images=["docker.io/library/nginx"])
        with self.assertRaises(Exception) as caught:
            self.run_check(cluster)
        self.assertIn("nginx", str(caught.exception))

    def test_pause_is_never_chosen_as_the_probe_image(self):
        """The probe overrides the command with a shell sleep, so a scratch image cannot be used.

        'pause' is present on every Kubernetes node, so a preference list containing it would pick it
        first on most labs - and it has no /bin/sh, so the command override would fail the container
        and the failure would present as a sidecar-injection problem.
        """
        self.assertNotIn("pause", IstioSidecarKeywords.SLEEPER_IMAGE_PREFERENCE)
        cluster = FakeCluster(registry_images=["registry.k8s.io/pause", "docker.io/library/busybox"])
        self.run_check(cluster)
        # busybox has a shell, so it must win over pause whatever order the registry reports them
        # in - pause is present on every node and would otherwise be an easy accidental choice.
        self.assertIn("busybox", cluster.rendered_images[0])

    def test_a_default_platform_registry_yields_a_shell_capable_image(self):
        """A default install has no busybox or alpine, so the fallbacks have to carry the check.

        This is the real image list from a 26.03 AIO-SX. The only candidates with a shell are
        curlimages/curl and ceph-config-helper; pause is present and would be picked first by a
        naive preference list, but it has no /bin/sh and the probe overrides the command.
        """
        default_platform_registry = [
            "docker.io/curlimages/curl",
            "docker.io/fluxcd/helm-controller",
            "docker.io/openstackhelm/ceph-config-helper",
            "quay.io/calico/node",
            "registry.k8s.io/kube-apiserver",
            "registry.k8s.io/pause",
        ]
        cluster = FakeCluster(registry_images=default_platform_registry, registry_tags=["8.17.0"])
        self.run_check(cluster)
        chosen = cluster.rendered_images[0]
        self.assertIn("curl", chosen)
        self.assertNotIn("pause", chosen)

    def test_an_untagged_image_fails_rather_than_pulling_latest(self):
        """A bare image name would resolve to :latest against a public registry and fail to pull."""
        cluster = FakeCluster(registry_tags=[])
        with self.assertRaises(Exception) as caught:
            self.run_check(cluster)
        self.assertIn("no tags", str(caught.exception))

    def test_a_namespace_that_will_not_delete_fails(self):
        """A cleanup failure on the happy path must fail the phase rather than warn.

        A namespace that will not delete leaves the next phase creating its artifacts against a
        half-deleted one, so it is a result rather than housekeeping.
        """
        cluster = FakeCluster()
        keywords = self.build(cluster)
        object.__setattr__(keywords, "get_namespaces", NonCallableMagicMock(wait_for_namespace_deleted=MagicMock(side_effect=[True, False])))
        with patch("keywords.cloud_platform.upgrade.istio_sidecar_keywords.ConfigurationManager") as config:
            config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = "registry.local:9001"
            with self.assertRaises(Exception) as caught:
                keywords.validate_sidecar_is_injected(self.request_stub(), "pre")
        self.assertIn("Terminating", str(caught.exception))


class TestWebhookRetry(IstioSidecarKeywordsTestBase):
    """The sidecar-injector webhook is served by istiod and may not answer immediately."""

    def test_a_webhook_that_is_still_starting_is_waited_out(self):
        """A create that fails because istiod is not answering yet is retried, not reported."""
        cluster = FakeCluster(apply_errors=["Error from server: no endpoints available for service istiod"])
        self.assertEqual(self.run_check(cluster), "1.29.2")

    def test_any_single_marker_is_enough_to_retry(self):
        """Requiring every marker at once would mean never retrying: istio uses several wordings."""
        for message in ["context deadline exceeded", "connection refused", "i/o timeout", "failed calling webhook"]:
            with self.subTest(message=message):
                cluster = FakeCluster(apply_errors=[f"Error from server: {message}"])
                self.assertEqual(self.run_check(cluster), "1.29.2")

    def test_an_unrelated_error_is_reported_immediately(self):
        """A real error must not be hidden behind the retry window."""
        cluster = FakeCluster(apply_errors=["Error from server (Forbidden): pods is forbidden"] * 50)
        with self.assertRaises(Exception) as caught:
            self.run_check(cluster)
        self.assertIn("Forbidden", str(caught.exception))


class TestProbePodPullSecret(IstioSidecarKeywordsTestBase):
    """The probe pod runs in a fresh namespace and needs its own registry credential."""

    def test_the_rendered_pod_carries_the_pull_secret(self):
        """Without imagePullSecrets the probe cannot pull, and that looks like an injection failure."""
        cluster = FakeCluster()
        keywords = self.build(cluster)
        with patch("keywords.cloud_platform.upgrade.istio_sidecar_keywords.ConfigurationManager") as config:
            config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = "registry.local:9001"
            captured = {}
            original = cluster.generate_yaml_file_from_template

            def capture(template_file: str, replacements: dict, target_file_name: str, target_remote_location: str) -> str:
                """Record each rendered document.

                Args:
                    template_file (str): template path.
                    replacements (dict): substitutions.
                    target_file_name (str): rendered name.
                    target_remote_location (str): remote directory.

                Returns:
                    str: the rendered path.
                """
                path = original(template_file, replacements, target_file_name, target_remote_location)
                captured[target_file_name] = cluster.rendered[path]
                return path

            object.__setattr__(keywords, "yaml", NonCallableMagicMock(generate_yaml_file_from_template=MagicMock(side_effect=capture)))
            keywords.validate_sidecar_is_injected(self.request_stub(), "pre")

        pods = [document for document in captured.values() if document["kind"] == "Pod"]
        self.assertTrue(pods, "no pod manifest was rendered")
        for pod in pods:
            self.assertEqual(pod["spec"]["imagePullSecrets"], [{"name": IstioSidecarKeywords.PULL_SECRET_NAME}])

    def test_the_secret_is_created_in_the_scratch_namespace(self):
        """The credential has to exist in the namespace the probe runs in."""
        cluster = FakeCluster()
        created = {}
        original = cluster.create_secret_for_registry

        def record(registry: object, secret_name: str, namespace: str = "default") -> None:
            """Record where the secret was created.

            Args:
                registry (object): the registry object.
                secret_name (str): the secret name.
                namespace (str): the namespace.
            """
            created["namespace"] = namespace
            created.setdefault("names", []).append(secret_name)
            original(registry, secret_name, namespace=namespace)

        cluster.create_secret_for_registry = record
        self.run_check(cluster)
        self.assertEqual(created["namespace"], "stxtest-istio-pre")
        self.assertEqual(created["names"], [IstioSidecarKeywords.PULL_SECRET_NAME, IstioSidecarKeywords.INJECTED_PULL_SECRET_NAME])

    def test_a_secret_that_was_not_created_fails(self):
        """The create verb does not assert, so the secret is read back and its absence must fail."""
        cluster = FakeCluster()
        cluster.create_secret_for_registry = lambda registry, secret_name, namespace="default": None
        with self.assertRaises(Exception) as caught:
            self.run_check(cluster)
        self.assertIn("pull secret", str(caught.exception))


class TestPerPhaseCleanupTracking(IstioSidecarKeywordsTestBase):
    """Cleanup is tracked per phase, so one phase's finalizer cannot delete another's namespace."""

    def test_a_finalizer_is_a_noop_once_its_phase_cleaned_up(self):
        """The happy path cleans up, so the registered finalizer must do nothing afterwards."""
        cluster = FakeCluster()
        keywords = self.build(cluster)
        request = self.request_stub()
        with patch("keywords.cloud_platform.upgrade.istio_sidecar_keywords.ConfigurationManager") as config:
            config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = "registry.local:9001"
            keywords.validate_sidecar_is_injected(request, "pre")

        deletions_before = len(cluster.deleted_namespaces)
        for finalizer in request.finalizers:
            finalizer()
        self.assertEqual(len(cluster.deleted_namespaces), deletions_before)

    def test_a_failed_phase_is_cleaned_up_by_its_finalizer(self):
        """A phase that failed before cleanup must still have its namespace removed."""
        cluster = FakeCluster()
        keywords = self.build(cluster)
        object.__setattr__(keywords, "label_namespace", NonCallableMagicMock(label_namespace=MagicMock()))
        request = self.request_stub()
        with patch("keywords.cloud_platform.upgrade.istio_sidecar_keywords.ConfigurationManager") as config:
            config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = "registry.local:9001"
            with self.assertRaises(Exception):
                keywords.validate_sidecar_is_injected(request, "pre")

        self.assertIn("stxtest-istio-pre", cluster.namespaces)
        for finalizer in request.finalizers:
            finalizer()
        self.assertNotIn("stxtest-istio-pre", cluster.namespaces)

    def test_one_phase_finalizer_does_not_delete_another_phases_namespace(self):
        """A shared cleanup flag would let an earlier finalizer delete a later phase's namespace."""
        cluster = FakeCluster()
        keywords = self.build(cluster)
        first_request = self.request_stub()
        with patch("keywords.cloud_platform.upgrade.istio_sidecar_keywords.ConfigurationManager") as config:
            config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = "registry.local:9001"
            keywords.validate_sidecar_is_injected(first_request, "pre")
            keywords.validate_sidecar_is_injected(self.request_stub(), "post-upgrade")

        self.assertEqual(keywords._cleaned_up_phases, {"pre", "post-upgrade"})
        deletions_before = len(cluster.deleted_namespaces)
        for finalizer in first_request.finalizers:
            finalizer()
        self.assertEqual(len(cluster.deleted_namespaces), deletions_before)

    def test_a_failed_phase_is_still_cleaned_up_after_an_earlier_phase_succeeded(self):
        """The cleanup record must be per phase, not one flag shared across the whole run.

        This is the case a happy-path-only test cannot see. One phase succeeds and records itself,
        then a later phase fails before it can clean up. With a per-phase record the failed phase is
        absent from it, so its finalizer removes its namespace. With a single shared flag the earlier
        phase's success makes the flag truthy, the later phase's finalizer decides someone already
        cleaned up, and that namespace leaks - which then makes the next run of the same phase fail on
        create.
        """
        cluster = FakeCluster()
        keywords = self.build(cluster)

        with patch("keywords.cloud_platform.upgrade.istio_sidecar_keywords.ConfigurationManager") as config:
            config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = "registry.local:9001"
            # First phase succeeds and records itself as cleaned up.
            keywords.validate_sidecar_is_injected(self.request_stub(), "pre")
            self.assertEqual(keywords._cleaned_up_phases, {"pre"})

            # Second phase fails before reaching its own cleanup.
            object.__setattr__(keywords, "label_namespace", NonCallableMagicMock(label_namespace=MagicMock()))
            failed_request = self.request_stub()
            with self.assertRaises(Exception):
                keywords.validate_sidecar_is_injected(failed_request, "post-upgrade")

        self.assertIn("stxtest-istio-post-upgrade", cluster.namespaces)
        for finalizer in failed_request.finalizers:
            finalizer()
        self.assertNotIn("stxtest-istio-post-upgrade", cluster.namespaces, "the failed phase's namespace leaked, so cleanup is not tracked per phase")


if __name__ == "__main__":
    unittest.main()
