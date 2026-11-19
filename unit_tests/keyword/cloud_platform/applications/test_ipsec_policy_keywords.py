"""Policy evidence and recovery tests independent of live test collection."""

import json
from unittest.mock import NonCallableMock, patch

import pytest

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.applications.ipsec_policy_keywords import IPsecPolicyKeywords
from keywords.cloud_platform.applications.ipsec_policy_state_keywords import OWNER_LABEL, IPsecPolicyStateKeywords
from keywords.cloud_platform.applications.object.ipsec_policy_images_output import IPsecPolicyImagesOutput
from keywords.cloud_platform.applications.object.ipsec_policy_list_output import IPsecPolicyListOutput
from keywords.cloud_platform.security.objects.ipsec_policy_sa_output import IPsecPolicySAOutput
from keywords.k8s.get_resource.object.kubernetes_resource_object import KubernetesResourceObject
from keywords.k8s.pods.object.pod_json_output import PodJsonOutput
from keywords.k8s.rollout.kubectl_rollout_status_keywords import KubectlRolloutStatusKeywords

SA = "list-sa event {k8s-node-controller-1 {uniqueid=1 state=ESTABLISHED local-host=192.0.2.1 remote-host=192.0.2.2 child-sas {flow-1 {name=tcp_probe_egress uniqueid=9 state=INSTALLED mode=TUNNEL local-ts=[10.1.0.0/24[tcp]] remote-ts=[10.2.0.3/32[tcp/18080]] bytes-in=120 packets-in=2 bytes-out=150 packets-out=3}}}}"
FLOW = ("192.0.2.1", "192.0.2.2", "10.1.0.7", "10.2.0.3", "tcp", 18080)


def test_parse_current_policy_tunnel():
    """Preserve identity, selectors and counters through SSH line output."""
    child = IPsecPolicySAOutput([SA + "\n"]).get_installed_tunnels()[0]
    assert child.matches_flow(*FLOW)
    assert child.get_counters() == {"bytes-in": 120, "packets-in": 2, "bytes-out": 150, "packets-out": 3}
    assert child.get_identity() == ("k8s-node-controller-1", "tcp_probe_egress", "9")


@pytest.mark.parametrize("index,value", [(0, "192.0.2.9"), (1, "192.0.2.8"), (2, "10.3.0.7"), (3, "10.2.0.4"), (4, "udp"), (5, 18081)])
def test_wrong_flow_never_matches(index, value):
    """A tunnel on another peer, address, protocol or port is unrelated evidence."""
    flow = list(FLOW)
    flow[index] = value
    assert not IPsecPolicySAOutput(SA).get_installed_tunnels()[0].matches_flow(*flow)


@pytest.mark.parametrize("output", ["", SA.replace("k8s-node-controller-1", "system-nodes"), SA.replace("ESTABLISHED", "CONNECTING"), SA.replace("INSTALLED", "INSTALLING"), SA.replace("TUNNEL", "TRANSPORT")])
def test_unrelated_or_incomplete_state_proves_nothing(output):
    """Empty, management and transitional associations do not become policy proof."""
    assert IPsecPolicySAOutput(output).get_installed_tunnels() == []


@pytest.mark.parametrize("output", ["error: disconnected", SA[:-1], SA + SA, SA.replace("packets-in=2", "packets-in=-1"), SA.replace("bytes-in=120", "bytes-in=unknown"), SA.replace("remote-ts=[10.2.0.3/32[tcp/18080]]", "remote-ts=[]"), SA.replace("uniqueid=9", "uniqueid=9 uniqueid=9"), SA.replace("[tcp/18080]", "[tcp/99999]"), SA.replace("bytes-out=150", "")])
def test_invalid_evidence_is_rejected(output):
    """Malformed, duplicate and missing observations fail explicitly."""
    with pytest.raises(ValueError):
        IPsecPolicySAOutput(output)


def test_ipv6_numeric_protocol_and_multiple_selectors():
    """Decode IPv6 selectors without confusing selector brackets with VICI lists."""
    text = SA.replace("192.0.2.1", "2001:db8::1").replace("192.0.2.2", "2001:db8::2").replace("10.1.0.0/24[tcp]", "2001:db8:1::/64[6]").replace("10.2.0.3/32[tcp/18080]", "2001:db8:2::3/128[6/18080] 2001:db8:2::4/128[6/18081]")
    assert IPsecPolicySAOutput(text).get_installed_tunnels()[0].matches_flow("2001:db8::1", "2001:db8::2", "2001:db8:1::7", "2001:db8:2::3", "tcp", 18080)


@pytest.fixture
def connection():
    """Provide checked mocked SSH without keyword logger side effects."""
    connection = NonCallableMock()
    connection.get_return_code.return_value = 0
    with patch("keywords.base_keyword.get_logger"), patch("framework.validation.validation.get_logger"):
        yield connection


def test_failed_command_cannot_parse_valid_looking_output(connection):
    """Validate the actual command failure path before constructing evidence."""
    connection.send_as_sudo_non_interactive.return_value = SA
    connection.get_return_code.return_value = 1
    with pytest.raises(Exception):
        IPsecPolicyKeywords(connection, "/config").read_policy_security_associations(connection)


def test_checked_sa_reader_uses_raw_mode(connection):
    """Wire real command output into the new parser without touching management APIs."""
    connection.send_as_sudo_non_interactive.return_value = [SA]
    output = IPsecPolicyKeywords(connection, "/config").read_policy_security_associations(connection)
    assert output.get_installed_tunnels()[0].matches_flow(*FLOW)
    connection.send_as_sudo_non_interactive.assert_called_once_with("swanctl --list-sas --raw")


def test_configmap_json_reading(connection):
    """Decode connection JSON inside the actual ConfigMap response envelope."""
    connection.send.return_value = json.dumps({"data": {"connections": "[]", "local_conn": "[]"}})
    output = IPsecPolicyKeywords(connection, "/config").get_node_configuration("controller-0")
    assert output.get_connections() == []
    assert output.get_local_connections() == []
    assert output.get_configuration_text() is None


def test_cleanup_continues_after_independent_failures(connection, monkeypatch):
    """A failed policy deletion cannot prevent workload cleanup or verification."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.captured = True
    first = {"kind": "Pod", "metadata": {"name": "client"}}
    second = {"kind": "IPsecPolicy", "metadata": {"name": "policy"}}
    state.resources = [first, second]
    calls = []

    def delete(manifest):
        calls.append(manifest["kind"])
        if manifest["kind"] == "IPsecPolicy":
            raise RuntimeError("policy failed")

    monkeypatch.setattr(state, "delete_owned_resource", delete)
    monkeypatch.setattr(state, "verify_baseline", lambda: calls.append("verify"))
    state.add_cleanup("restore", lambda: calls.append("restore"))
    with pytest.raises(KeywordException, match="policy failed"):
        state.restore_state()
    assert calls == ["IPsecPolicy", "Pod", "restore", "verify"]


def test_lost_apply_reply_retains_cleanup_intent(connection, monkeypatch):
    """A remotely successful mutation with a lost reply stays registered."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.captured = True
    manifest = {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": state.run_id, "labels": {OWNER_LABEL: state.run_id}}}
    monkeypatch.setattr(state, "_find_owned_resource", lambda manifest: None)
    with patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.KubectlFileApplyKeywords") as apply:
        apply.return_value.apply_resource_from_yaml.side_effect = RuntimeError("lost reply")
        with pytest.raises(RuntimeError, match="lost reply"):
            state.apply_owned_resource(manifest)
    assert state.resources == [manifest]
    assert len(state.files) == 1


def test_foreign_resource_is_never_overwritten(connection, monkeypatch):
    """Even a matching name is insufficient to establish test ownership."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.captured = True
    manifest = {"kind": "Namespace", "metadata": {"name": state.run_id, "labels": {OWNER_LABEL: state.run_id}}}
    monkeypatch.setattr(state, "_find_owned_resource", lambda manifest: {"metadata": {"labels": {OWNER_LABEL: "someone-else"}}})
    with pytest.raises(KeywordException, match="another actor"):
        state.apply_owned_resource(manifest)
    connection.send.assert_not_called()


def test_mutation_requires_registered_recovery(connection):
    """Uncaptured fixtures may not create anything."""
    with pytest.raises(KeywordException, match="Capture"):
        IPsecPolicyStateKeywords(connection, "/config").apply_owned_resource({})
    connection.send.assert_not_called()


@pytest.mark.parametrize("output,count", [(SA + "\nlist-sas reply {}", 1), ("list-sas reply {}", 0)])
def test_terminal_vici_reply(output, count):
    """Handle the terminal reply emitted by swanctl's real raw command handler."""
    assert len(IPsecPolicySAOutput(output).get_installed_tunnels()) == count


@pytest.mark.parametrize("output", ["list-sas reply {errmsg=failed}", "list-sas reply {}" + SA])
def test_invalid_terminal_reply(output):
    """Diagnostics or events after a completion reply are not valid evidence."""
    with pytest.raises(ValueError):
        IPsecPolicySAOutput(output)


def test_candidate_digests_are_compared_per_role(connection, monkeypatch):
    """A matching application version cannot hide the wrong running image."""
    reader = IPsecPolicyKeywords(connection, "/config")
    expected = {"agent": {"manager": "sha256:" + "a" * 64}, "manager": {"manager": "sha256:" + "b" * 64}}
    provenance = {"application_revision": "review/1", "automation_revision": "worktree/2", "build_reference": "candidate-build"}
    observed = {"agent/controller-0": expected["agent"], "manager/pod-1": expected["manager"]}
    monkeypatch.setattr(reader, "get_running_images", lambda: IPsecPolicyImagesOutput(observed))
    with patch("keywords.cloud_platform.applications.ipsec_policy_keywords.SystemApplicationListKeywords") as applications, patch("keywords.cloud_platform.applications.ipsec_policy_keywords.get_logger"):
        applications.return_value.get_application_state.return_value = ("candidate", "applied")
        assert reader.verify_candidate("candidate", expected, provenance).get_container_images("agent/controller-0") == expected["agent"]
        observed["agent/controller-0"] = {"manager": "sha256:" + "c" * 64}
        with pytest.raises(Exception, match="Validation Failed"):
            reader.verify_candidate("candidate", expected, provenance)


def test_last_policy_delete_requires_exclusive_lab(connection, monkeypatch):
    """A shared lab cannot silently enter last-policy cleanup."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    manifest = {"kind": "IPsecPolicy", "metadata": {"name": state.run_id, "labels": {OWNER_LABEL: state.run_id}}}
    state.resources.append(manifest)
    monkeypatch.setattr(state, "_find_owned_resource", lambda value: KubernetesResourceObject(manifest))
    monkeypatch.setattr(state.policy_keywords, "get_policies", lambda: IPsecPolicyListOutput(json.dumps({"items": [{"metadata": {"name": state.run_id, "uid": "policy"}, "spec": {}}]})))
    with pytest.raises(KeywordException, match="exclusive"):
        state.delete_owned_resource(manifest)
    connection.send.assert_not_called()


def test_cleanup_after_namespace_already_removed(connection):
    """Repeated recovery treats a confirmed absent namespace as absent workloads."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    connection.send.return_value = '{"items":[]}'
    manifest = {"kind": "Pod", "metadata": {"name": state.run_id + "-client", "namespace": state.run_id}}
    state.resources.append(manifest)
    state.delete_owned_resource(manifest)
    assert connection.send.call_count == 1
    assert "namespaces" in connection.send.call_args.args[0]


@pytest.mark.parametrize("personality,ready,expected", [("storage", True, "Storage"), ("worker", False, "not Ready")])
def test_topology_rejects_storage_and_unready_nodes(connection, personality, ready, expected):
    """Independently discovered inventory overrides pod-only readiness claims."""
    reader = IPsecPolicyKeywords(connection, "/config")
    host = NonCallableMock()
    host.get_host_name.return_value = "node-a"
    host.get_personality.return_value = personality
    host.get_administrative.return_value = "unlocked"
    host.get_operational.return_value = "enabled"
    host.get_availability.return_value = "available"
    connection.send.return_value = json.dumps({"items": [{"metadata": {"name": "node-a"}, "status": {"conditions": [{"type": "Ready", "status": "True" if ready else "False"}]}}]})
    with patch("keywords.cloud_platform.applications.ipsec_policy_keywords.KubectlGetDaemonsetsKeywords") as daemonsets, patch("keywords.cloud_platform.applications.ipsec_policy_keywords.SystemHostListKeywords") as hosts:
        daemonsets.return_value.get_daemonset_workload.return_value.get_eligible_nodes.return_value = ("node-a",)
        hosts.return_value.get_system_host_list.return_value.get_hosts.return_value = [host]
        with pytest.raises(KeywordException, match=expected):
            reader.get_eligible_nodes()


def test_application_upload_lost_reply_retains_outer_recovery(connection):
    """Register application recovery before the first upload mutation."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    connection.send.side_effect = ["metadata.yaml", "app_name: ipsec-policy-operator\napp_version: candidate"]
    finalizers = []
    with patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationListKeywords") as applications, patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationUploadKeywords") as upload:
        applications.return_value.get_application_state.return_value = None
        upload.return_value.system_application_upload.side_effect = RuntimeError("lost upload reply")
        with pytest.raises(RuntimeError, match="lost upload reply"):
            state.prepare_application(finalizers.append, "/scratch/candidate.tgz", "candidate", exclusive=True)
    assert len(finalizers) == 1
    assert state.original_application is None


def test_application_removal_preserves_remaining_policies(connection, monkeypatch):
    """Whole-app recovery must not remove pre-existing or uncleaned policies."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.original_application = None
    monkeypatch.setattr(state.policy_keywords, "has_policy_crd", lambda: True)
    monkeypatch.setattr(state.policy_keywords, "get_policies", lambda: IPsecPolicyListOutput(json.dumps({"items": [{"metadata": {"name": "foreign", "uid": "foreign-uid"}, "spec": {}}]})))
    with patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationListKeywords") as applications, patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationRemoveKeywords") as remove:
        applications.return_value.get_application_state.return_value = ("candidate", "applied")
        with pytest.raises(KeywordException, match="Policies remain"):
            state.restore_application()
        remove.assert_not_called()


def test_invalid_candidate_images_fail_before_override_mutation(connection):
    """Invalid candidate inputs must fail before any Helm operation."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.captured = True
    state.application = ("candidate", "applied")
    provenance = {"application_revision": "a", "automation_revision": "b", "build_reference": "c"}
    with pytest.raises(KeywordException, match="image identities"):
        state.prepare_candidate("candidate", {}, provenance, {"ipsec-policy-agent": {"changed": True}})
    connection.send.assert_not_called()


def test_application_recovery_waits_for_transition(connection):
    """Recovery rereads the state after the shared bounded transition wait."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.original_application = ("candidate", "uploaded")
    with patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationListKeywords") as applications:
        applications.return_value.get_application_state.side_effect = [("candidate", "removing"), ("candidate", "uploaded")]
        state.restore_application()
        applications.return_value.validate_app_status_in_list.assert_called_once()
        assert applications.return_value.get_application_state.call_count == 2


def test_application_recovery_timeout_does_not_mutate(connection):
    """A stuck transition remains a failure instead of triggering unsafe cleanup."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.original_application = None
    with patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationListKeywords") as applications, patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationRemoveKeywords") as remove:
        applications.return_value.get_application_state.return_value = ("candidate", "applying")
        applications.return_value.validate_app_status_in_list.side_effect = TimeoutError("still applying")
        with pytest.raises(TimeoutError, match="still applying"):
            state.restore_application()
        remove.assert_not_called()


def test_agent_wait_retries_only_missing_scheduling_labels(connection):
    """Retry late labels without hiding unsupported scheduling errors."""
    reader = IPsecPolicyKeywords(connection, "/config")
    with patch("keywords.cloud_platform.applications.ipsec_policy_keywords.KubectlGetDaemonsetsKeywords") as daemonsets, patch("keywords.cloud_platform.applications.ipsec_policy_keywords.KubectlWaitPodKeywords") as wait, patch("keywords.cloud_platform.applications.ipsec_policy_keywords.validate_equals_with_retry") as retry:
        eligible = daemonsets.return_value.get_daemonset_workload.return_value.get_matching_nodes
        eligible.side_effect = [(), ("controller-0",), ValueError("unsupported scheduling")]

        def poll(function, *args, **kwargs):
            assert function() is False
            assert function() is True
            with pytest.raises(ValueError, match="unsupported scheduling"):
                function()

        retry.side_effect = poll
        wait.return_value.wait_for_daemonset_ready.return_value = {"controller-0": {}}
        assert reader.wait_for_agents_ready() == {"controller-0": {}}


def test_package_update_registers_recovery_before_lost_reply(connection, monkeypatch):
    """A lost update reply retains reverse-update recovery and original identity."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.captured = state.exclusive = True
    state.application = ("original", "applied")
    state.charts = {}
    archives = []
    monkeypatch.setattr(state, "validate_application_archive", lambda path, version: archives.append((path, version)))
    monkeypatch.setattr(state.policy_keywords, "get_running_images", lambda: {"agent/node": {"manager": "digest"}})
    updates = []

    def update(path, version):
        updates.append((path, version))
        if version == "candidate":
            assert len(state.cleanups) == 1
            raise RuntimeError("lost reply")

    monkeypatch.setattr(state, "_update_application_archive", update)
    monkeypatch.setattr(state, "_reapply_baseline", lambda images: None)
    with pytest.raises(RuntimeError, match="lost reply"):
        state.update_candidate_package("/candidate.tgz", "candidate", "/original.tgz")
    assert archives == [("/candidate.tgz", "candidate"), ("/original.tgz", "original")]
    with patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationListKeywords") as applications:
        applications.return_value.get_application_state.return_value = ("candidate", "applied")
        state.cleanups[0][1]()
    assert updates[-1] == ("/original.tgz", "original")


def test_override_failure_restores_each_chart_before_reapply(connection, monkeypatch):
    """A partial override update preserves independent reverse-order restoration."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.captured = state.exclusive = True
    state.application = ("original", "applied")
    charts = ["ipsec-policy-agent", "ipsec-policy-manager"]
    state.charts = {chart: {"user_overrides": {"original": chart}} for chart in charts}
    calls = []
    monkeypatch.setattr(state.policy_keywords, "get_running_images", lambda timeout=300: {})

    def set_values(chart, values):
        calls.append((chart, values))
        if chart == charts[1] and values == {"candidate": True}:
            raise RuntimeError("partial update")

    monkeypatch.setattr(state, "_set_chart_overrides", set_values)
    monkeypatch.setattr(state, "_reapply_baseline", lambda images: calls.append("reapply"))
    monkeypatch.setattr(state, "verify_baseline", lambda: calls.append("verify"))
    images = {role: {"manager": "sha256:" + "a" * 64} for role in ("agent", "manager")}
    provenance = {"application_revision": "app", "automation_revision": "test", "build_reference": "build"}
    with pytest.raises(RuntimeError, match="partial update"):
        state.prepare_candidate("original", images, provenance, {chart: {"candidate": True} for chart in charts})
    state.restore_state()
    assert calls[-4:] == [(charts[1], {"original": charts[1]}), (charts[0], {"original": charts[0]}), "reapply", "verify"]


@pytest.mark.parametrize("has_crd", [False, True])
def test_partial_apply_recovery_checks_crd_before_policy_read(connection, has_crd):
    """Confirmed absent CRDs allow recovery; present ones require policy reads."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.original_application = ("candidate", "uploaded")
    connection.send.return_value = json.dumps({"items": [{"metadata": {"name": "ipsecpolicies.starlingx.io"}}] if has_crd else []})
    with patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationListKeywords") as applications, patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationRemoveKeywords") as remove, patch.object(state.policy_keywords, "get_policies", return_value=IPsecPolicyListOutput('{"items":[]}')) as policies:
        applications.return_value.get_application_state.side_effect = [("candidate", "apply-failed"), state.original_application]
        state.restore_application()
        assert policies.call_count == int(has_crd)
        remove.return_value.system_application_remove.assert_called_once()


def test_crd_command_failure_blocks_destructive_recovery(connection):
    """API/transport failure is not evidence that no policies exist."""
    state = IPsecPolicyStateKeywords(connection, "/config")
    state.original_application = None
    connection.send.return_value = '{"items":[]}'
    connection.get_return_code.return_value = 1
    with patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationListKeywords") as applications, patch("keywords.cloud_platform.applications.ipsec_policy_state_keywords.SystemApplicationRemoveKeywords") as remove:
        applications.return_value.get_application_state.return_value = ("candidate", "apply-failed")
        with pytest.raises(AssertionError):
            state.restore_application()
        remove.assert_not_called()


def test_manager_snapshot_waits_for_old_terminating_pod(connection):
    """A ready current manager plus a terminating historical pod is pending."""
    reader = IPsecPolicyKeywords(connection, "/config")
    deployment = {"metadata": {"uid": "deployment", "generation": 2}, "spec": {"replicas": 1}, "status": {"observedGeneration": 2, "updatedReplicas": 1, "readyReplicas": 1, "availableReplicas": 1, "replicas": 1}}
    replicasets = {"items": [{"metadata": {"uid": name, "ownerReferences": [{"uid": "deployment", "controller": True}]}} for name in ("old", "current")]}
    current = {"metadata": {"name": "current-pod", "ownerReferences": [{"uid": "current", "controller": True}]}, "spec": {"containers": [{"name": "manager"}]}, "status": {"containerStatuses": [{"name": "manager", "ready": True, "state": {"running": {}}, "imageID": "registry/image@sha256:" + "a" * 64}]}}
    old = {"metadata": {"name": "old-pod", "deletionTimestamp": "2026-11-10T00:00:00Z", "ownerReferences": [{"uid": "old", "controller": True}]}}
    with patch("keywords.cloud_platform.applications.ipsec_policy_keywords.KubectlGetResourceKeywords") as resources:
        resources.return_value.get_resource_field.side_effect = [json.dumps(value) for value in (deployment, replicasets, {"items": [current, old]}, deployment, replicasets, {"items": [current]})]
        assert reader._get_manager_images() is None
        assert reader._get_manager_images().get_container_images("manager/current-pod") == {"manager": "sha256:" + "a" * 64}


def test_manager_pending_uses_bounded_poll_and_returns_evidence(connection, monkeypatch):
    """Production image collection must wire pending snapshots to bounded polling."""
    reader = IPsecPolicyKeywords(connection, "/config")
    monkeypatch.setattr(reader, "wait_for_agents_ready", lambda timeout=300: {})
    observations = iter([None, IPsecPolicyImagesOutput({"manager/current": {"manager": "sha256:" + "a" * 64}})])
    monkeypatch.setattr(reader, "_get_manager_images", lambda timeout=300: next(observations))
    with patch("keywords.cloud_platform.applications.ipsec_policy_keywords.validate_equals_with_retry") as retry:

        def poll(function, *args, **kwargs):
            assert kwargs["timeout"] == 300
            assert function().get_value_to_validate() is False
            return function().get_value_to_return()

        retry.side_effect = poll
        assert reader.get_running_images().get_container_images("manager/current") == {"manager": "sha256:" + "a" * 64}


def test_typed_policy_snapshot_is_independent_of_source_and_returned_spec(connection):
    """Snapshot getters preserve identity and cannot mutate the recovery baseline."""
    resource = {"metadata": {"name": "policy", "uid": "original"}, "spec": {"policies": [{"name": "service"}]}}
    connection.send.return_value = json.dumps({"items": [resource]})
    output = IPsecPolicyKeywords(connection, "/config").get_policies()
    policy = output.get_policies()[0]
    assert policy.get_name() == "policy"
    assert policy.get_uid() == "original"
    spec = policy.get_spec()
    spec["policies"].clear()
    assert policy.get_spec()["policies"] == [{"name": "service"}]


@pytest.mark.parametrize("image_id", ["registry/image@sha256:" + "a" * 64, "containerd://sha256:" + "a" * 64, "docker://sha256:" + "a" * 64])
def test_shared_container_digest_normalization(image_id):
    """Agent and manager image parsing use the same runtime normalization."""
    pod = {"status": {"containerStatuses": [{"name": "manager", "imageID": image_id}]}}
    assert PodJsonOutput(pod).get_container_digests() == {"manager": "sha256:" + "a" * 64}


def test_child_sa_getters_preserve_selector_snapshot():
    """Child model exposes explicit identity and isolated selector accessors."""
    child = IPsecPolicySAOutput(SA).get_installed_tunnels()[0]
    assert child.get_local_host() == "192.0.2.1"
    assert child.get_remote_host() == "192.0.2.2"
    assert child.get_name() == "tcp_probe_egress"
    selectors = child.get_local_selectors()
    selectors.clear()
    assert child.get_local_selectors() == ["10.1.0.0/24[tcp]"]


def test_rollout_keyword_quotes_identifiers_and_respects_timeout(connection):
    """The shared rollout operation preserves command status and wait bounds."""
    keyword = KubectlRolloutStatusKeywords(connection, "/config")
    keyword.wait_for_deployment_rollout("space;unsafe", "manager;unsafe", timeout=12)
    command = connection.send.call_args.args[0]
    assert "deployment/'manager;unsafe'" in command
    assert "-n 'space;unsafe'" in command
    assert "--timeout=12s" in command
    assert connection.send.call_args.kwargs["command_timeout"] == 32
    connection.get_return_code.return_value = 1
    with pytest.raises(AssertionError):
        keyword.wait_for_deployment_rollout("namespace", "manager", timeout=12)


@pytest.mark.parametrize("change", ["none", "missing-policy", "policy-spec", "policy-uid", "chart-overrides", "chart-attributes", "node-label"])
def test_original_configuration_snapshot_survives_release_change(connection, change):
    """Retain original policy/settings evidence while allowing app version changes."""
    module = "keywords.cloud_platform.applications.ipsec_policy_state_keywords"
    policy = {"metadata": {"name": "original", "uid": "uid"}, "spec": {"policies": [{"name": "service"}]}}
    state = IPsecPolicyStateKeywords(connection, "/config")
    baseline = IPsecPolicyListOutput(json.dumps({"items": [policy]}))
    nodes = {"items": [{"metadata": {"name": "node-a", "labels": {"ipsec-policy-agent-operator": "enabled"}}}]}
    connection.send.return_value = json.dumps(nodes)
    with patch(module + ".SystemApplicationListKeywords") as applications, patch(module + ".SystemHelmOverrideKeywords") as helm, patch.object(state.policy_keywords, "get_policies", return_value=baseline) as policies:
        applications.return_value.get_application_state.return_value = ("26.03-1", "applied")
        helm.return_value.get_system_helm_override_show.return_value.get_helm_override_show.return_value.get_attributes.return_value = {"enabled": True}
        helm.return_value.get_user_override_values.return_value = {"config": "original"}
        state.capture_baseline(exclusive=True)
        applications.return_value.get_application_state.return_value = ("27.03-2", "applied")
        if change == "missing-policy":
            policies.return_value = IPsecPolicyListOutput('{"items": []}')
        elif change in ("policy-spec", "policy-uid"):
            if change == "policy-spec":
                policy["spec"] = {}
            else:
                policy["metadata"]["uid"] = "replacement"
            policies.return_value = IPsecPolicyListOutput(json.dumps({"items": [policy]}))
        elif change == "chart-overrides":
            helm.return_value.get_user_override_values.return_value = {}
        elif change == "chart-attributes":
            helm.return_value.get_system_helm_override_show.return_value.get_helm_override_show.return_value.get_attributes.return_value = {"enabled": False}
        elif change == "node-label":
            nodes["items"][0]["metadata"]["labels"] = {}
            connection.send.return_value = json.dumps(nodes)
        if change == "none":
            state.verify_configuration()
        else:
            with pytest.raises(KeywordException):
                state.verify_configuration()
