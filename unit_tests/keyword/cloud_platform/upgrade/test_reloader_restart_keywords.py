"""Unit tests for the reloader reload-delivery check.

These run against a stateful in-memory stand-in for the cluster rather than a sequence of canned
return values. That matters here because the whole question is causal: a watched ConfigMap changes
and the consuming workload must be rolled *as a consequence*. A scripted list of return values would
report a successful reload even if the keyword never changed anything, or changed the wrong
resource, or read the answer before acting.

The model therefore implements reloader rather than simulating its output. It watches which
ConfigMaps and Secrets each workload consumes through envFrom, checks for the reloader annotation on
the Deployment, and only then bumps the generation, replaces the pod and re-snapshots the pod's
environment. Every failure mode the check exists to catch is a knob on the model - a dead reloader,
one that ignores annotations, one that rolls without delivering - so the tests assert on behaviour
the model produced, not on values the test dictated.

The real manifest template is rendered and parsed, so the probe's shape is covered to the extent
that a structural change - a lost envFrom, a second container, a missing pull secret - is visible to
the model. It is not a substitute for applying the manifest to a cluster: nothing here validates
that Kubernetes accepts it.

No validate_* function is patched. Failures surface as the exceptions production code would raise.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import NonCallableMagicMock, patch

import yaml

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.registry.registry_image_resolver_keywords import RegistryImageResolverKeywords
from keywords.cloud_platform.upgrade.reloader_restart_keywords import ReloaderRestartKeywords

PULL_SECRET = "default-registry-key"
# Where the platform actually seeds the pull secret. Three existing test cases copy it out of
# kube-system into a target namespace, and the default namespace holds no secrets at all on a
# freshly configured system.
PULL_SECRET_SOURCE_NAMESPACE = "kube-system"


def _resolver_backed_by(cluster: object) -> object:
    """Build a real image resolver whose registry reads come from the cluster model.

    The resolver is exercised for real rather than stubbed out, so the selection rules it owns stay
    covered from here as well as from its own tests.

    Args:
        cluster (object): the cluster model answering the registry reads.

    Returns:
        object: a RegistryImageResolverKeywords wired to that model.
    """
    resolver = RegistryImageResolverKeywords.__new__(RegistryImageResolverKeywords)
    object.__setattr__(resolver, "registry_images", SimpleNamespace(is_registry_reachable=cluster.is_registry_reachable, get_registry_image_list=cluster.get_registry_image_list))
    object.__setattr__(resolver, "registry_tags", SimpleNamespace(get_image_tags=cluster.get_image_tags))
    return resolver


class FakeCluster:
    """A small stateful stand-in for the cluster, implementing reloader's actual behaviour."""

    def __init__(self, reloader_dead: bool = False, ignored_kinds: set = None, annotation_blind: bool = False, deliver_stale: bool = False, suppress_rollout: bool = False, observed_lag: bool = False, stuck_ready: str = None, unready_polls: int = 0, ready_lag_polls: int = 0, exec_fail_polls: int = 0, sa_delay_polls: int = 0, namespace_delete_polls: int = 0, drop_env_key: bool = False, rollout_in_flight: bool = False, registry_images: list = None, registry_tags: list = None, unstable_tag_order: bool = False, registry_reachable: bool = True):
        """Build an empty cluster.

        Args:
            reloader_dead (bool): reloader never reacts to a watched change.
            ignored_kinds (set): watch paths reloader is deaf to, for example {"Secret"}. Models
                one path regressing while the other keeps working, which reloader_dead cannot
                express because it disables both at once.
            annotation_blind (bool): reloader rolls every workload, annotated or not.
            deliver_stale (bool): the workload rolls but the new pod keeps the old environment.
            suppress_rollout (bool): the generation advances but no new pod appears.
            observed_lag (bool): status.observedGeneration never catches up to metadata.generation.
            stuck_ready (str): when set, every pod reports this READY string forever.
            unready_polls (int): how many initial readiness reads report the pod as not ready,
                modelling a container that has not started because the image is still pulling.
                An exec into such a pod fails.
            ready_lag_polls (int): how many initial readiness reads report the pod as not ready
                while its container is running, modelling a readiness probe that has not
                passed yet. An exec into such a pod succeeds, which is what separates this
                from unready_polls.
            exec_fail_polls (int): how many initial execs fail against a pod that is ready,
                modelling a transient exec failure rather than a pod that is not up.
            sa_delay_polls (int): reads of a new namespace's default ServiceAccount that fail first.
            namespace_delete_polls (int): polls a deleted namespace lingers for, modelling Terminating.
            drop_env_key (bool): the probe's ConfigMap omits the watched key, so printenv exits non-zero.
            rollout_in_flight (bool): the first read after a roll reports both the old and new pod.
            registry_images (list): image names the local registry reports. Defaults to busybox.
            registry_tags (list): tags the registry reports for the chosen image.
            unstable_tag_order (bool): whether the registry returns the tags in a different
                order on each call, which a registry is under no obligation not to do.
            registry_reachable (bool): whether the local registry answers at all.
        """
        self.namespaces = {}
        self.rendered = {}
        # Keyed (namespace, name) throughout. The platform seeds the local registry pull secret into
        # kube-system, and a scratch namespace starts without it, so copying it in is setup rather
        # than an optimisation. Modelling where it actually lives is what lets a wrong source
        # namespace fail here instead of on hardware.
        self.secrets = {(PULL_SECRET_SOURCE_NAMESPACE, PULL_SECRET): {"seeded": "yes"}}
        self.configmaps = {}
        self.workloads = {}
        self.deleted_namespaces = []
        # Which delete verb each removal came through, to pin that teardown cannot raise.
        self.delete_verbs = []
        # The return code of the last pod exec. The real exec keyword, when told not to assert the
        # return code, leaves the caller to inspect it, and the SSH layer combines stderr into
        # stdout - so a failed exec returns its error text as though it were output. Modelling the
        # return code is what lets a caller that ignores it fail here rather than on hardware.
        self.last_exec_rc = 0
        self.service_accounts = set()
        self.sa_delay_polls = sa_delay_polls
        self._sa_reads_remaining = {}
        self.reloader_dead = reloader_dead
        self.ignored_kinds = set() if ignored_kinds is None else set(ignored_kinds)
        self.annotation_blind = annotation_blind
        self.deliver_stale = deliver_stale
        self.suppress_rollout = suppress_rollout
        self.observed_lag = observed_lag
        self.stuck_ready = stuck_ready
        self.unready_polls = unready_polls
        self.ready_lag_polls = ready_lag_polls
        self.exec_fail_polls = exec_fail_polls
        self._ready_lag_remaining = {}
        self._unready_remaining = {}
        # The ready string last reported for a workload, so that an exec sees the same pod
        # state the readiness read just reported. Reads happen in that order in one snapshot.
        self._last_ready = {}
        self._uid_counter = 0
        self.rolled = []
        self.namespace_delete_polls = namespace_delete_polls
        self._terminating = {}
        self.drop_env_key = drop_env_key
        self.rollout_in_flight = rollout_in_flight
        self.registry_images = ["docker.io/library/busybox"] if registry_images is None else registry_images
        self.registry_tags = ["1.37"] if registry_tags is None else registry_tags
        self.unstable_tag_order = unstable_tag_order
        # How often the registry was asked, to pin that discovery happens once per run.
        self.tag_queries = 0
        # Every image reference the probe was rendered with, to prove the choice is stable.
        self.rendered_images = []
        self.registry_reachable = registry_reachable
        self._in_flight = set()
        # Teardown deletes namespaces and rendered files, so anything a test needs to inspect after
        # a completed phase is also recorded here. Without this, a construction test that runs the
        # whole phase first inspects an empty cluster and passes vacuously - one of them did.
        self.workload_history = []
        self.rendered_history = {}

    # --- namespace lifecycle ---------------------------------------------------------------

    def create_namespaces(self, name: str) -> None:
        """Create a namespace, failing if it exists, as the real asserting verb does.

        Args:
            name (str): namespace name.

        Raises:
            AssertionError: when the namespace already exists.
        """
        if name in self.namespaces:
            raise AssertionError(f"namespace {name} already exists")
        self.namespaces[name] = True
        if self.sa_delay_polls <= 0:
            self.service_accounts.add(name)
        else:
            self._sa_reads_remaining[name] = self.sa_delay_polls

    def delete_namespace(self, name: str) -> None:
        """Delete a namespace and everything in it.

        Args:
            name (str): namespace name.
        """
        self.delete_verbs.append("asserting")
        if self.namespace_delete_polls > 0:
            self._terminating[name] = self.namespace_delete_polls
            self.deleted_namespaces.append(name)
            return
        self.namespaces.pop(name, None)
        self.deleted_namespaces.append(name)
        for store in (self.configmaps, self.secrets, self.workloads):
            for key in [k for k in store if k[0] == name]:
                store.pop(key)

    def cleanup_namespace(self, name: str) -> str:
        """Delete a namespace without failing on a non-zero return code.

        The tolerant counterpart of delete_namespace, used in teardown. It issues the same delete
        but never reports a problem, so a namespace that lingers in Terminating cannot turn teardown
        into an error of its own.

        Args:
            name (str): namespace name.

        Returns:
            str: the return code of the delete, always "0" here.
        """
        self.delete_namespace(name)
        self.delete_verbs[-1] = "tolerant"
        return "0"

    def get_namespaces(self) -> SimpleNamespace:
        """Return an object answering whether a namespace is present.

        Returns:
            SimpleNamespace: exposes is_namespace(name).
        """

        def _is_namespace(name: str) -> bool:
            """Report presence, letting a Terminating namespace linger for a few polls.

            Args:
                name (str): namespace name.

            Returns:
                bool: True while the namespace is still present.
            """
            remaining = self._terminating.get(name, 0)
            if remaining > 0:
                self._terminating[name] = remaining - 1
                if remaining - 1 == 0:
                    self.namespaces.pop(name, None)
                    for store in (self.configmaps, self.secrets, self.workloads):
                        for existing in [k for k in store if k[0] == name]:
                            store.pop(existing)
                return True
            return name in self.namespaces

        return SimpleNamespace(is_namespace=_is_namespace)

    def read_service_account(self, namespace: str) -> str:
        """Return the default ServiceAccount name once the controller has created it.

        Args:
            namespace (str): namespace to read.

        Returns:
            str: "default" when present, empty string while still pending.
        """
        if namespace in self.service_accounts:
            return "default"
        remaining = self._sa_reads_remaining.get(namespace, 0)
        # The controller creates it after a few polls regardless of whether anyone is reading, so a
        # read does not cause it. A keyword that skips the wait therefore creates its pod too early.
        if remaining <= 1:
            self._sa_reads_remaining.pop(namespace, None)
            self.service_accounts.add(namespace)
            return "default"
        self._sa_reads_remaining[namespace] = remaining - 1
        return ""

    # --- rendering and applying ------------------------------------------------------------

    def render(self, template_file: str, replacement_dictionary: dict, target_file_name: str, target_remote_location: str, copy_to_remote: bool = True, preserve_order: bool = False) -> str:
        """Render a template into the fake filesystem, matching YamlKeywords' real signature.

        Args:
            template_file (str): local template path.
            replacement_dictionary (dict): template variables.
            target_file_name (str): rendered file name.
            target_remote_location (str): remote directory.
            copy_to_remote (bool): unused here; present to match the real signature.
            preserve_order (bool): unused here; present to match the real signature.

        Returns:
            str: the rendered file path.
        """
        with open(template_file) as handle:
            body = handle.read()
        for key, value in replacement_dictionary.items():
            body = body.replace("{{" + key + "}}", str(value))
        path = f"{target_remote_location}/{target_file_name}"
        self.rendered[path] = body
        self.rendered_history[path] = body
        if "image" in replacement_dictionary:
            self.rendered_images.append(replacement_dictionary["image"])
        return path

    def apply(self, path: str) -> None:
        """Apply a rendered manifest, running reloader's reaction as a consequence.

        Args:
            path (str): the rendered file path.

        Raises:
            AssertionError: when the manifest was never rendered, or names a missing namespace.
        """
        if path not in self.rendered:
            raise AssertionError(f"nothing rendered at {path}")
        for doc in yaml.safe_load_all(self.rendered[path]):
            if doc:
                self._apply_doc(doc)

    def _apply_doc(self, doc: dict) -> None:
        """Apply one manifest document.

        Args:
            doc (dict): the parsed document.

        Raises:
            AssertionError: when the namespace does not exist.
        """
        kind = doc["kind"]
        meta = doc["metadata"]
        namespace = meta.get("namespace")
        if namespace not in self.namespaces:
            raise AssertionError(f"namespace {namespace} does not exist")
        key = (namespace, meta["name"])
        if kind == "ConfigMap":
            data = dict(doc.get("data") or {})
            if self.drop_env_key:
                data.pop("PROBE_CONFIGMAP_VALUE", None)
            changed = self.configmaps.get(key) != data
            self.configmaps[key] = data
            if changed:
                self._react(namespace, meta["name"], "ConfigMap")
        elif kind == "Secret":
            changed = self.secrets.get(key) != doc.get("stringData")
            self.secrets[key] = doc.get("stringData", {})
            if changed:
                self._react(namespace, meta["name"], "Secret")
        elif kind == "Deployment":
            annotated = "reloader.stakater.com/auto" in (meta.get("annotations") or {})
            containers = doc["spec"]["template"]["spec"]["containers"]
            if namespace not in self.service_accounts:
                # Admission rejects a pod whose ServiceAccount does not exist yet. This surfaces on
                # the create, not as a pod condition, so no pod-level retry recovers from it.
                raise AssertionError(f"error: pods is forbidden: error looking up service account {namespace}/default")
            existing = self.workloads.get(key)
            if existing is None:
                self.workloads[key] = {
                    "annotated": annotated,
                    "containers": containers,
                    "label": doc["spec"]["selector"]["matchLabels"]["app"],
                    "generation": 1,
                    "observed": 1,
                    "uid": self._next_uid(),
                    "env": self._resolve_env(namespace, containers),
                    "pull_secrets": [s["name"] for s in doc["spec"]["template"]["spec"].get("imagePullSecrets", [])],
                }
                self.workload_history.append(dict(self.workloads[key], name=meta["name"]))
                return
            # Re-applying an unchanged Deployment is a no-op in kubectl: the generation does not move
            # and no pod is replaced. Modelling it as a recreate would wipe reloader's reaction, and
            # then the check could never observe a roll it had actually caused.
            if existing["containers"] == containers and existing["annotated"] == annotated:
                return
            existing["annotated"] = annotated
            existing["containers"] = containers
            existing["generation"] += 1
            existing["observed"] = existing["generation"] if not self.observed_lag else existing["observed"]
            existing["uid"] = self._next_uid()
            existing["env"] = self._resolve_env(namespace, containers)

    def _next_uid(self) -> str:
        """Return a fresh pod UID.

        Returns:
            str: a unique identifier.
        """
        self._uid_counter += 1
        return f"pod-uid-{self._uid_counter}"

    def _resolve_env(self, namespace: str, containers: list) -> dict:
        """Resolve the environment a pod would start with, from its envFrom sources.

        Args:
            namespace (str): the workload namespace.
            containers (list): the pod template's containers.

        Returns:
            dict: the resolved environment.
        """
        env = {}
        for source in containers[0].get("envFrom", []):
            if "configMapRef" in source:
                env.update(self.configmaps.get((namespace, source["configMapRef"]["name"]), {}))
            if "secretRef" in source:
                env.update(self.secrets.get((namespace, source["secretRef"]["name"]), {}))
        return env

    def _react(self, namespace: str, resource_name: str, kind: str) -> None:
        """Roll every workload that consumes the changed resource, as reloader would.

        Args:
            namespace (str): the namespace of the changed resource.
            resource_name (str): the changed resource's name.
            kind (str): "ConfigMap" or "Secret".
        """
        if self.reloader_dead or kind in self.ignored_kinds:
            return
        ref = "configMapRef" if kind == "ConfigMap" else "secretRef"
        for key, workload in self.workloads.items():
            if key[0] != namespace:
                continue
            consumes = any(source.get(ref, {}).get("name") == resource_name for source in workload["containers"][0].get("envFrom", []))
            if not consumes:
                continue
            if not workload["annotated"] and not self.annotation_blind:
                continue
            workload["generation"] += 1
            if not self.observed_lag:
                workload["observed"] = workload["generation"]
            if not self.suppress_rollout:
                workload["uid"] = self._next_uid()
                if self.rollout_in_flight:
                    self._in_flight.add(key[1])
                if not self.deliver_stale:
                    workload["env"] = self._resolve_env(namespace, workload["containers"])
            self.rolled.append(key[1])

    # --- reads -----------------------------------------------------------------------------

    def get_resource_field(self, resource_type: str, resource_name: str, jsonpath: str, namespace: str = None) -> str:
        """Read one field from a resource.

        Args:
            resource_type (str): the resource kind.
            resource_name (str): the resource name.
            jsonpath (str): the jsonpath expression.
            namespace (str): the namespace.

        Returns:
            str: the field value, or an empty string when absent.
        """
        if resource_type == "serviceaccount":
            return self.read_service_account(namespace)
        workload = self.workloads.get((namespace, resource_name))
        if workload is None:
            return ""
        if "observedGeneration" in jsonpath:
            return str(workload["observed"])
        if "generation" in jsonpath:
            return str(workload["generation"])
        return ""

    def _container_started(self, namespace: str, workload: dict) -> bool:
        """Return whether the pod's container is running, and so can be exec'd into.

        Args:
            namespace (str): the namespace.
            workload (dict): the workload record.

        Returns:
            bool: True when an exec would succeed.
        """
        if PULL_SECRET not in workload["pull_secrets"] or (namespace, PULL_SECRET) not in self.secrets:
            return False
        return self._unready_remaining.get((namespace, workload["label"]), self.unready_polls) <= 0

    def _ready_string(self, namespace: str, workload: dict) -> str:
        """Return the READY column for a workload's pod.

        Args:
            namespace (str): the namespace.
            workload (dict): the workload record.

        Returns:
            str: the ready string, for example "1/1".
        """
        total = len(workload["containers"])
        if PULL_SECRET not in workload["pull_secrets"] or (namespace, PULL_SECRET) not in self.secrets:
            # ImagePullBackOff: a scratch namespace has no pull secret, so the image never pulls and
            # the pod never becomes ready.
            return f"0/{total}"
        key = (namespace, workload["label"])
        if key not in self._unready_remaining:
            self._unready_remaining[key] = self.unready_polls
        if self._unready_remaining.get(key, 0) > 0:
            # The ordinary case of a pod that exists but whose container has not started yet,
            # because the image is still being pulled.
            self._unready_remaining[key] -= 1
            return f"0/{total}"
        if key not in self._ready_lag_remaining:
            self._ready_lag_remaining[key] = self.ready_lag_polls
        if self._ready_lag_remaining.get(key, 0) > 0:
            # The container is running, so an exec succeeds, but the pod is not ready yet.
            self._ready_lag_remaining[key] -= 1
            return f"0/{total}"
        return self.stuck_ready or f"{total}/{total}"

    def get_pods(self, namespace: str = None, label: str = None) -> SimpleNamespace:
        """Return the pods of a labelled workload.

        Args:
            namespace (str): the namespace.
            label (str): the workload label selector value.

        Returns:
            SimpleNamespace: exposes get_pods() returning pod stand-ins.
        """
        wanted = label.split("=", 1)[1] if label and "=" in label else label
        found = []
        for key, workload in self.workloads.items():
            if key[0] != namespace or (wanted and workload["label"] != wanted):
                continue
            total = len(workload["containers"])
            ready = self._ready_string(namespace, workload)
            self._last_ready[(namespace, workload["label"])] = ready
            found.append(SimpleNamespace(get_name=lambda w=workload: f"{w['label']}-{w['uid']}", get_ready=lambda r=ready: r))
            if self.rollout_in_flight and key[1] in self._in_flight:
                # One poll reports the outgoing pod alongside the new one, oldest first. A reader
                # that takes items[0] without checking the count reads the pod that is going away.
                self._in_flight.discard(key[1])
                found.insert(0, SimpleNamespace(get_name=lambda: "outgoing-pod", get_ready=lambda: f"{total}/{total}"))
        return SimpleNamespace(get_pods=lambda: found)

    def is_registry_reachable(self, command_timeout: int = 120) -> bool:
        """Report whether the local registry answers.

        Args:
            command_timeout (int): unused; present to match the real signature.

        Returns:
            bool: True when reachable.
        """
        return self.registry_reachable

    def get_registry_image_list(self, command_timeout: int = 120) -> SimpleNamespace:
        """Return the registry's image listing.

        Args:
            command_timeout (int): unused; present to match the real signature.

        Returns:
            SimpleNamespace: exposes get_image_names().
        """
        return SimpleNamespace(get_image_names=lambda: list(self.registry_images))

    def get_image_tags(self, image_name: str, command_timeout: int = 120) -> SimpleNamespace:
        """Return the tags the registry reports for an image.

        Args:
            image_name (str): the image name.
            command_timeout (int): unused; present to match the real signature.

        Returns:
            SimpleNamespace: exposes get_tag_names().
        """
        self.tag_queries += 1
        if self.unstable_tag_order:
            self.registry_tags = list(reversed(self.registry_tags))
        return SimpleNamespace(get_tag_names=lambda: list(self.registry_tags))

    def get_pod_uid_by_name(self, pod_name: str, namespace: str = "default") -> str:
        """Return a pod's UID, derived from its name.

        Args:
            pod_name (str): the pod name.
            namespace (str): the namespace.

        Returns:
            str: the pod UID.
        """
        for key, workload in self.workloads.items():
            if key[0] == namespace and f"{workload['label']}-{workload['uid']}" == pod_name:
                return workload["uid"]
        return ""

    def run_pod_exec_cmd(self, pod_name: str, cmd: str, options: str = "", ignore_error: bool = False) -> str:
        """Read an environment variable from inside a pod.

        Args:
            pod_name (str): the pod name.
            cmd (str): the command, expected to be a printenv.
            options (str): kubectl options carrying the namespace.
            ignore_error (bool): whether a non-zero return code is tolerated.

        Returns:
            str: the variable's value, the error text of a failed exec, or an empty string when the
                variable is unset.
        """
        namespace = options.split()[-1] if options else "default"
        tokens = cmd.replace("'", " ").split()
        variable = tokens[tokens.index("printenv") + 1] if "printenv" in tokens else ""
        self.last_exec_rc = 0
        for key, workload in self.workloads.items():
            if key[0] == namespace and f"{workload['label']}-{workload['uid']}" == pod_name:
                if self.exec_fail_polls > 0:
                    # A transient exec failure against a pod that is up. The error text comes back
                    # as output, so only the return code distinguishes it from a real value.
                    self.exec_fail_polls -= 1
                    self.last_exec_rc = 1
                    return "error: unable to upgrade connection: error dialing backend: EOF"
                if not self._container_started(namespace, workload):
                    # kubectl exec into a pod whose container has not started fails, and because the
                    # SSH layer combines stderr into stdout the error text comes back as output.
                    # Returning it as a value is what makes an unready pod look readable.
                    self.last_exec_rc = 1
                    return "error: unable to upgrade connection: container not found"
                if variable not in workload["env"] and not ignore_error:
                    # printenv exits 1 for an unset variable, and the real keyword asserts the
                    # return code unless ignore_error is set.
                    raise AssertionError("Return code was 1")
                return workload["env"].get(variable, "")
        self.last_exec_rc = 1
        return f'error: pods "{pod_name}" not found'

    def get_secret_names(self, namespace: str = "default") -> list:
        """Return the secret names in a namespace.

        Args:
            namespace (str): the namespace.

        Returns:
            list: secret names.
        """
        return [name for (ns, name) in self.secrets if ns == namespace]

    def copy_secret_between_namespaces(self, secret_name: str, source_namespace: str, target_namespace: str) -> None:
        """Copy a secret into another namespace.

        Args:
            secret_name (str): the secret name.
            source_namespace (str): the source namespace.
            target_namespace (str): the target namespace.

        Raises:
            AssertionError: when the secret is absent from the source namespace, as kubectl's own
                get-then-create would fail.
        """
        if (source_namespace, secret_name) not in self.secrets:
            raise AssertionError(f"secret {secret_name} does not exist in namespace {source_namespace}")
        self.secrets[(target_namespace, secret_name)] = {"copied": "yes"}

    def delete_file(self, path: str) -> bool:
        """Remove a rendered file.

        Args:
            path (str): the file path.

        Returns:
            bool: always True.
        """
        self.rendered.pop(path, None)
        return True


class ReloaderRestartKeywordsTestBase(unittest.TestCase):
    """Shared wiring for the reload-delivery tests."""

    def setUp(self):
        """Silence loggers and shorten every wait so the suite runs without sleeping."""
        self.patchers = [
            patch("keywords.base_keyword.get_logger"),
            patch("keywords.cloud_platform.upgrade.reloader_restart_keywords.get_logger"),
            patch("framework.validation.validation.get_logger"),
            patch("keywords.cloud_platform.system.registry.registry_image_resolver_keywords.get_logger"),
            # The probe image is resolved from the local registry by the shared resolver, and the
            # registry URL comes from the docker config. Patched to a fixed host so the rendered
            # reference is deterministic. Patched in the resolver's module, which is where the read
            # now happens.
            patch("keywords.cloud_platform.system.registry.registry_image_resolver_keywords.ConfigurationManager", **{"get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value": "registry.local:9001"}),
            patch.object(ReloaderRestartKeywords, "ROLLOUT_TIMEOUT", 2),
            patch.object(ReloaderRestartKeywords, "ROLLOUT_POLL_INTERVAL", 0),
            patch.object(ReloaderRestartKeywords, "POD_READY_TIMEOUT", 2),
            patch.object(ReloaderRestartKeywords, "POD_READY_POLL_INTERVAL", 0),
            patch.object(ReloaderRestartKeywords, "SERVICE_ACCOUNT_TIMEOUT", 2),
            patch.object(ReloaderRestartKeywords, "SERVICE_ACCOUNT_POLL_INTERVAL", 0),
            patch.object(ReloaderRestartKeywords, "NAMESPACE_DELETE_TIMEOUT", 2),
            patch.object(ReloaderRestartKeywords, "NAMESPACE_DELETE_INTERVAL", 0),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.addCleanup(self._stop_patchers)
        self.request = SimpleNamespace(addfinalizer=lambda fn: self.finalizers.append(fn))
        self.finalizers = []

    def _stop_patchers(self):
        """Stop every patcher."""
        for patcher in self.patchers:
            patcher.stop()

    def build(self, cluster: FakeCluster) -> ReloaderRestartKeywords:
        """Return a keyword instance wired to a cluster model.

        BaseKeyword.__getattribute__ wraps callable attributes in a logging wrapper, so collaborators
        are installed with object.__setattr__ and built from NonCallableMagicMock.

        Args:
            cluster (FakeCluster): the cluster model to wire in.

        Returns:
            ReloaderRestartKeywords: instance backed by that model.
        """
        keywords = ReloaderRestartKeywords.__new__(ReloaderRestartKeywords)

        def stub(**methods: object) -> NonCallableMagicMock:
            """Build a non-callable mock exposing the given bound methods.

            Args:
                **methods (object): attribute name to callable.

            Returns:
                NonCallableMagicMock: the stub.
            """
            mock = NonCallableMagicMock()
            for name, method in methods.items():
                setattr(mock, name, method)
            return mock

        install = lambda name, value: object.__setattr__(keywords, name, value)  # noqa: E731
        install("ssh_connection", stub(get_return_code=lambda: cluster.last_exec_rc))
        install("create_namespace", stub(create_namespaces=cluster.create_namespaces))
        install("delete_namespace", stub(delete_namespace=cluster.delete_namespace, cleanup_namespace=cluster.cleanup_namespace))
        install("get_namespaces", stub(get_namespaces=cluster.get_namespaces))
        install("yaml", stub(generate_yaml_file_from_template=cluster.render))
        install("file_apply", stub(apply_resource_from_yaml=cluster.apply))
        install("files", stub(delete_file=cluster.delete_file))
        install("resources", stub(get_resource_field=cluster.get_resource_field))
        install("pods", stub(get_pods=cluster.get_pods, get_pod_uid_by_name=cluster.get_pod_uid_by_name))
        install("exec", stub(run_pod_exec_cmd=cluster.run_pod_exec_cmd))
        install("get_secrets", stub(get_secret_names=cluster.get_secret_names))
        install("create_secret", stub(copy_secret_between_namespaces=cluster.copy_secret_between_namespaces))
        install("image_resolver", _resolver_backed_by(cluster))
        install("_cleaned_up_phases", set())
        # __new__ bypasses the constructor, so plain fields are installed here too.
        install("_probe_image", None)
        return keywords


class TestReloadDelivers(ReloaderRestartKeywordsTestBase):
    """The happy path, and the failure modes the check exists to catch."""

    def test_a_working_reloader_passes(self):
        """A reloader that rolls the annotated probe and delivers the value, leaving the control."""
        cluster = FakeCluster()
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(cluster.rolled, "the model never rolled anything, so the check proved nothing")

    def test_a_dead_reloader_fails(self):
        """No watched change produces a roll, which is the failure the reload check must detect."""
        with self.assertRaises(TimeoutError) as caught:
            self.build(FakeCluster(reloader_dead=True)).validate_reload_delivers(self.request, "pre")
        self.assertIn("ConfigMap change must roll", str(caught.exception))

    def test_a_reloader_deaf_to_configmaps_only_fails_on_the_configmap_leg(self):
        """The ConfigMap watch path must be able to fail on its own.

        The two watch paths are separate concerns, and the realistic post-upgrade regression is one
        of them going deaf while the other keeps working - lost RBAC on secrets, say. The failure is
        required to name the kind, because every knob in this model produces the same TimeoutError
        and a type-only assertion would pass when the other leg was what broke.
        """
        with self.assertRaises(TimeoutError) as caught:
            self.build(FakeCluster(ignored_kinds={"ConfigMap"})).validate_reload_delivers(self.request, "pre")
        self.assertIn("ConfigMap change must roll", str(caught.exception))

    def test_a_reloader_deaf_to_secrets_only_fails_on_the_secret_leg(self):
        """The Secret watch path must be able to fail on its own.

        Without a per-kind switch there is no such test at all: a reloader that reacts to nothing
        fails the ConfigMap leg first, the retry raises, and the Secret assertion never executes. So
        the Secret path - the one other work depends on - has no failing case.
        """
        with self.assertRaises(TimeoutError) as caught:
            self.build(FakeCluster(ignored_kinds={"Secret"})).validate_reload_delivers(self.request, "pre")
        self.assertIn("Secret change must roll", str(caught.exception))

    def test_a_reloader_that_rolls_without_delivering_fails(self):
        """The workload rolls but the new pod keeps the old environment: a restart, not a reload."""
        with self.assertRaises(TimeoutError) as caught:
            self.build(FakeCluster(deliver_stale=True)).validate_reload_delivers(self.request, "pre")
        self.assertIn("ConfigMap change must roll", str(caught.exception))

    def test_a_suppressed_rollout_fails(self):
        """The generation advances but no new pod appears."""
        with self.assertRaises(TimeoutError) as caught:
            self.build(FakeCluster(suppress_rollout=True)).validate_reload_delivers(self.request, "pre")
        self.assertIn("ConfigMap change must roll", str(caught.exception))

    def test_an_unobserved_generation_fails(self):
        """The controller never acts on the new generation."""
        with self.assertRaises(TimeoutError) as caught:
            self.build(FakeCluster(observed_lag=True)).validate_reload_delivers(self.request, "pre")
        self.assertIn("ConfigMap change must roll", str(caught.exception))

    def test_an_annotation_blind_reloader_fails(self):
        """Rolling the unannotated control too means annotations are being ignored.

        This is what the negative control is for: without it, anything that rolls workloads in this
        namespace would satisfy every probe-side assertion.
        """
        with self.assertRaises(TimeoutError) as caught:
            self.build(FakeCluster(annotation_blind=True)).validate_reload_delivers(self.request, "pre")
        self.assertIn("ConfigMap change must roll", str(caught.exception))

    def test_a_probe_that_never_becomes_ready_fails(self):
        """A pod that comes up and never reports ready has delivered nothing."""
        with self.assertRaises(TimeoutError) as caught:
            self.build(FakeCluster(stuck_ready="0/1")).validate_reload_delivers(self.request, "pre")
        self.assertIn("must come up and become readable", str(caught.exception))


class TestProbeConstruction(ReloaderRestartKeywordsTestBase):
    """Properties of the rendered probe that the assertions depend on."""

    def test_the_probe_consumes_through_envfrom_not_a_volume(self):
        """A projected volume is synced in place, so a file read would pass with reloader deleted."""
        cluster = FakeCluster()
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        manifests = "\n".join(cluster.rendered_history.values())
        self.assertIn("envFrom", manifests)
        self.assertNotIn("volumeMounts", manifests)

    def test_the_probe_is_single_container_and_single_replica(self):
        """reloader's default strategy injects into the first container; one replica removes ambiguity."""
        cluster = FakeCluster()
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertEqual(len(cluster.workload_history), 2, "a probe and a control must have been created")
        for workload in cluster.workload_history:
            self.assertEqual(len(workload["containers"]), 1, f"{workload['name']} must have exactly one container")
        self.assertIn("replicas: 1", "\n".join(cluster.rendered_history.values()))

    def test_the_control_is_not_annotated_and_has_its_own_resources(self):
        """Shared resources would make the control unable to distinguish reloader from anything else."""
        cluster = FakeCluster()
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        annotated = [w for w in cluster.workload_history if w["annotated"]]
        unannotated = [w for w in cluster.workload_history if not w["annotated"]]
        self.assertEqual(len(annotated), 1, "exactly one annotated probe")
        self.assertEqual(len(unannotated), 1, "exactly one unannotated control")
        self.assertNotEqual(annotated[0]["containers"][0]["envFrom"], unannotated[0]["containers"][0]["envFrom"], "probe and control must not share resources")

    def test_the_pull_secret_is_copied_into_the_scratch_namespace(self):
        """A scratch namespace has no pull secret, so the probe could not pull its image."""
        cluster = FakeCluster()
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertEqual(len(cluster.workload_history), 2, "a probe and a control must have been created")
        for workload in cluster.workload_history:
            self.assertIn(PULL_SECRET, workload["pull_secrets"], f"{workload['name']} had no pull secret")


class TestProbeImageDiscovery(ReloaderRestartKeywordsTestBase):
    """The probe image is discovered, because a pinned reference fails to pull on the wrong lab."""

    def test_the_reference_carries_a_host_and_a_tag(self):
        """A bare repository name resolves to an implicit :latest against a public registry.

        That fails to pull, and an unpullable probe looks exactly like the reload failure this check
        exists to detect. The sibling sidecar check records both the missing host prefix and the
        assumed tag as failures observed on hardware.
        """
        cluster = FakeCluster(registry_images=["docker.io/library/busybox"], registry_tags=["1.37"])
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        manifests = "\n".join(cluster.rendered_history.values())
        self.assertIn("registry.local:9001/docker.io/library/busybox:1.37", manifests)

    def test_preference_order_is_honoured(self):
        """The first candidate present wins, so a lab carrying several is deterministic."""
        cluster = FakeCluster(registry_images=["docker.io/library/alpine", "docker.io/library/busybox"], registry_tags=["3.20"])
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertIn("busybox:3.20", "\n".join(cluster.rendered_history.values()))

    def test_an_unreachable_registry_fails_before_anything_is_created(self):
        """Failing early names the real cause instead of a pod that never pulls."""
        cluster = FakeCluster(registry_reachable=False)
        with self.assertRaises(KeywordException) as caught:
            self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertIn("not reachable", str(caught.exception))

    def test_no_candidate_image_fails_naming_what_it_looked_for(self):
        """A lab with none of the candidates cannot run this check, and should say so."""
        cluster = FakeCluster(registry_images=["docker.io/library/nginx"])
        with self.assertRaises(KeywordException) as caught:
            self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertIn("no probe image matching", str(caught.exception))
        self.assertIn("busybox", str(caught.exception))

    def test_an_image_with_no_tags_fails(self):
        """An untagged image cannot be pulled, so it is not a usable probe image."""
        cluster = FakeCluster(registry_tags=[])
        with self.assertRaises(KeywordException) as caught:
            self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertIn("no tags", str(caught.exception))


class TestNamespaceLifecycle(ReloaderRestartKeywordsTestBase):
    """Setup ordering and teardown, which earlier siblings got wrong."""

    def test_it_waits_for_the_default_service_account(self):
        """Creating a pod before the ServiceAccount exists is an admission error no retry recovers."""
        cluster = FakeCluster(sa_delay_polls=2)
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(cluster.rolled, "the run must still succeed once the ServiceAccount appears")

    def test_the_probe_image_is_chosen_once_and_does_not_change_between_applies(self):
        """A registry may list tags in any order, and the probe image must not follow it.

        The image is substituted into both the probe and the control, so a reference that changes
        between applies re-templates both of them. The control would then advance its generation
        and replace its pod for a reason that has nothing to do with reloader, and the phase would
        fail reporting that reloader ignored annotations.
        """
        cluster = FakeCluster(registry_tags=["1.37.0", "1.36.1"], unstable_tag_order=True)
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(cluster.rendered_images, "no probe image was ever rendered")
        self.assertEqual(
            len(set(cluster.rendered_images)),
            1,
            f"the probe image changed between applies: {cluster.rendered_images}",
        )

    def test_the_registry_is_consulted_once_rather_than_on_every_apply(self):
        """Discovery is setup, not part of applying, and each apply would otherwise re-ask.

        A phase applies the manifest three times, so resolving the image inside the apply turns one
        question to the registry into three, on a path where every answer must agree with the last.
        """
        cluster = FakeCluster()
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertEqual(cluster.tag_queries, 1, f"the registry was asked for tags {cluster.tag_queries} times")

    def test_the_probe_image_name_is_chosen_by_a_stated_rule(self):
        """Two repositories can satisfy the same preference, and the listing order must not decide.

        The preference list narrows the choice to a substring, not to one repository: a registry
        holding the same candidate under two paths leaves the match ambiguous, and resolving it by
        listing position makes the probe image depend on something the registry never promised.
        """
        cluster = FakeCluster(registry_images=["docker.io/z-mirror/busybox", "docker.io/a-mirror/busybox"])
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(cluster.rendered_images, "no probe image was ever rendered")
        self.assertIn("a-mirror/busybox", cluster.rendered_images[0], f"expected the sorted-first name, got {cluster.rendered_images[0]}")

    def test_the_probe_image_tag_is_chosen_by_a_stated_rule(self):
        """The tag is selected by sorting, so the same registry contents always give the same image.

        Which tag is immaterial for a throwaway probe - any tag that pulls will do - so the rule is
        chosen for being reproducible rather than for preferring the newest.
        """
        cluster = FakeCluster(registry_tags=["1.37.0", "1.36.1"])
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(cluster.rendered_images, "no probe image was ever rendered")
        self.assertTrue(
            cluster.rendered_images[0].endswith(":1.36.1"),
            f"expected the sorted-first tag, got {cluster.rendered_images[0]}",
        )

    def test_a_failed_exec_is_not_mistaken_for_a_value(self):
        """The error text of a failed exec must not be read as the environment's contents.

        The SSH layer folds stderr into stdout, so a failed exec returns its error text where a
        value would be, and that text is not empty. Only the return code separates the two. Taken
        as a value it would be compared against the expected ConfigMap contents and fail, against
        a pod that was up and a reloader that was working.
        """
        cluster = FakeCluster(exec_fail_polls=2)
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(cluster.rolled, "a transient exec failure must cost a poll, not the phase")

    def test_it_waits_out_a_pod_that_is_running_but_not_yet_ready(self):
        """Readiness has to be waited for, not asserted once the environment becomes readable.

        A running container can be exec'd into before its pod reports ready, so the environment
        read succeeds while READY is still 0/1. Asserting readiness after the wait rather than
        including it in the wait fails a system that was only a poll away from being ready.
        """
        cluster = FakeCluster(ready_lag_polls=2)
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(cluster.rolled, "the run must succeed once the pod reports ready")

    def test_it_waits_out_a_pod_whose_container_has_not_started(self):
        """An exec into an unready pod must not be mistaken for a reading of its environment.

        The pod exists before its container does, so the exec fails and - because the SSH layer
        folds stderr into stdout - returns its error text where a value would be. Treating that as
        a value makes the snapshot look readable, ends the wait early, and fails the readiness
        assertion on a system that was merely still pulling the image.
        """
        cluster = FakeCluster(unready_polls=2)
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(cluster.rolled, "the run must succeed once the container starts")

    def test_the_namespace_is_removed_on_the_happy_path(self):
        """Teardown leaves no scratch namespace behind."""
        cluster = FakeCluster()
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(cluster.deleted_namespaces, "the scratch namespace was never deleted")

    def test_a_finalizer_is_registered_before_anything_is_created(self):
        """Registered first, so a setup that fails part way through still cleans up."""
        cluster = FakeCluster()
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(self.finalizers, "no cleanup finalizer was registered")

    def test_teardown_after_a_failure_cannot_raise_over_the_real_failure(self):
        """The finalizer deletes tolerantly, because a failed phase is what leaves a wedged namespace.

        A namespace that will not finish Terminating is most likely precisely when the phase has
        already failed. The asserting verb would spend its whole timeout there and then raise, so
        the reported error would be the teardown rather than the failure that mattered.
        """
        cluster = FakeCluster(reloader_dead=True)
        with self.assertRaises(TimeoutError) as caught:
            self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertIn("ConfigMap change must roll", str(caught.exception))
        for finalizer in self.finalizers:
            finalizer()
        self.assertEqual(cluster.delete_verbs[-1:], ["tolerant"], f"teardown used {cluster.delete_verbs}")

    def test_the_finalizer_cleans_up_after_a_failure(self):
        """A run that failed mid-phase must not leave its namespace behind."""
        cluster = FakeCluster(reloader_dead=True)
        keywords = self.build(cluster)
        with self.assertRaises(TimeoutError) as caught:
            keywords.validate_reload_delivers(self.request, "pre")
        self.assertIn("ConfigMap change must roll", str(caught.exception))
        for finalizer in self.finalizers:
            finalizer()
        self.assertTrue(cluster.deleted_namespaces, "the finalizer did not remove the namespace")

    def test_it_tolerates_a_namespace_that_lingers_in_terminating(self):
        """Deletion is asynchronous, so the confirmation must wait rather than assume.

        Without the confirmation the next phase collides with a namespace that is still going away,
        and a leaked namespace is exactly what the asserting delete verb exists to prevent.
        """
        cluster = FakeCluster(namespace_delete_polls=2)
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertNotIn("stxtest-reloader-pre", cluster.namespaces, "the namespace was never actually removed")

    def test_a_missing_watched_key_does_not_end_the_run_by_raising(self):
        """printenv exits non-zero for an unset variable, and the exec keyword asserts by default.

        The read sits inside a retry window that retries values and does not catch exceptions, so a
        raising read would end the run with its timeout budget unspent instead of failing on the
        value. It must degrade to the sentinel and let the window time out on its own terms.
        """
        with self.assertRaises(TimeoutError) as caught:
            self.build(FakeCluster(drop_env_key=True)).validate_reload_delivers(self.request, "pre")
        self.assertIn("must come up and become readable", str(caught.exception))
        self.assertNotIn("Return code was 1", str(caught.exception), "the environment read raised instead of degrading to its sentinel")

    def test_it_ignores_the_outgoing_pod_while_a_rollout_is_in_flight(self):
        """Two pods exist mid-roll, and the oldest is reported first.

        A reader that takes the first pod without checking the count reads the pod that is going
        away, so the identity comparison sees the old UID and the roll is never observed.
        """
        cluster = FakeCluster(rollout_in_flight=True)
        self.build(cluster).validate_reload_delivers(self.request, "pre")
        self.assertTrue(cluster.rolled, "the roll was never observed")

    def test_each_phase_uses_its_own_namespace(self):
        """Phase-scoped resources, so no state crosses an upgrade boundary."""
        cluster = FakeCluster()
        keywords = self.build(cluster)
        keywords.validate_reload_delivers(self.request, "pre")
        keywords.validate_reload_delivers(self.request, "post-upgrade")
        self.assertEqual(len(set(cluster.deleted_namespaces)), 2, "phases shared a namespace")


if __name__ == "__main__":
    unittest.main()
