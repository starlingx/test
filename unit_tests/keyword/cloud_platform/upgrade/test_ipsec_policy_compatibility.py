"""Policy compatibility orchestration and recovery boundaries."""

from unittest.mock import Mock, NonCallableMock, patch

import pytest

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.upgrade.ipsec_policy_compatibility_keywords import IPsecPolicyCompatibilityKeywords
from testcases.cloud_platform.upgrade.app_compat import test_ipsec_policy_upgrade_compat as case

MODULE = "keywords.cloud_platform.upgrade.ipsec_policy_compatibility_keywords"


@pytest.fixture(autouse=True)
def configure_logging():
    """Supply framework logging for isolated keyword execution."""
    with patch("keywords.base_keyword.get_logger"), patch("framework.validation.validation.get_logger"), patch("config.configuration_manager.ConfigurationManager.get_k8s_config", return_value=Mock(get_kubeconfig=lambda: "/config")):
        yield


def test_round_trip_checks_all_phases(monkeypatch):
    """The actual test calls enforcement before, after upgrade and after rollback."""
    mocks = {}
    for name in ("LabConnectionKeywords", "SoftwareDeploySequenceKeywords", "StandardPlatformUpgradeKeywords", "UpgradeRecoveryKeywords", "ApplicationHealthKeywords", "PlatformUpgradePreparationKeywords", "IPsecPolicyCompatibilityKeywords", "ConfigurationManager", "get_logger"):
        mocks[name] = Mock()
        monkeypatch.setattr(case, name, mocks[name])
    mocks["IPsecPolicyCompatibilityKeywords"].normalize_platform_release.side_effect = IPsecPolicyCompatibilityKeywords.normalize_platform_release
    deploy = mocks["SoftwareDeploySequenceKeywords"].return_value
    deploy.get_running_release.side_effect = ["26.03.0", "26.10.0", "26.03"]
    deploy.get_current_deploy_state.return_value = ""
    health = mocks["ApplicationHealthKeywords"].return_value
    health.get_app_version.side_effect = ["26.03-1", "26.10-2", "26.03-1"]
    health.get_app_or_deploy_alarm_count.return_value = 0
    config = mocks["ConfigurationManager"].get_app_upgrade_compat_config.return_value
    config.get_to_version.return_value = "26.10"
    config.get_ipsec_traffic_image.return_value = "image@sha256:" + "a" * 64
    monkeypatch.setattr(case, "validate_equals_with_retry", lambda reader, expected, *args, **kwargs: reader() == expected)
    request = Mock()
    case.test_ipsec_policy_upgrade_rollback(request)
    compatibility = mocks["IPsecPolicyCompatibilityKeywords"].return_value
    compatibility.capture_original_configuration.assert_called_once_with()
    assert [call.args[1] for call in compatibility.verify_enforcement.call_args_list] == ["pre", "post-upgrade", "post-rollback"]
    platform = mocks["StandardPlatformUpgradeKeywords"].return_value
    platform.upgrade_platform_in_order.assert_called_once_with(deploy, "26.10", leave_at_activate_done=True)
    platform.rollback_platform_in_order.assert_called_once_with(deploy)
    request.addfinalizer.call_args.args[0]()
    mocks["UpgradeRecoveryKeywords"].return_value.restore_to_release.assert_called_once_with("26.03")


@pytest.mark.parametrize("failure", [False, True])
def test_phase_cleanup_is_registered_and_disarmed(failure):
    """A successful phase cannot restore old-release snapshots during teardown."""
    with patch(MODULE + ".IPsecPolicyKeywords") as policy, patch(MODULE + ".IPsecPolicyTrafficKeywords") as factory, patch(MODULE + ".IPsecPolicyStateKeywords", return_value=NonCallableMock()), patch(MODULE + ".LabConnectionKeywords"), patch(MODULE + ".get_logger"):
        policy.return_value = NonCallableMock()
        policy.return_value.get_eligible_nodes.return_value.get_node_names.return_value = ("a", "b")
        traffic = factory.return_value
        cleanup = Mock()
        traffic.capture_state.side_effect = lambda register, **kwargs: register(cleanup)
        if failure:
            traffic.verify_policy_traffic.side_effect = KeywordException("traffic failed")
        finalizers = []
        keyword = IPsecPolicyCompatibilityKeywords(Mock())
        if failure:
            with pytest.raises(KeywordException, match="traffic failed"):
                keyword.verify_enforcement(finalizers.append, "pre", "image", ("a", "b"))
            assert cleanup.call_count == 0
        else:
            keyword.verify_enforcement(finalizers.append, "pre", "image", ("a", "b"))
            assert cleanup.call_count == 2
        for finalizer in reversed(finalizers):
            finalizer()
        assert cleanup.call_count == (1 if failure else 2)


@pytest.mark.parametrize("source,target,image", [("bad", "26.10", "image"), ("26.10", "26.03", "image"), ("26.03", "26.10", "image:latest")])
def test_invalid_inputs_rejected_before_discovery(source, target, image):
    """Bad releases or mutable images cannot initiate platform changes."""
    with patch(MODULE + ".IPsecPolicyKeywords") as policy:
        with pytest.raises(KeywordException):
            IPsecPolicyCompatibilityKeywords(Mock()).validate_inputs(source, target, image)
        policy.return_value.get_eligible_nodes.assert_not_called()


@pytest.mark.parametrize("phase", ["post-upgrade", "post-rollback"])
def test_original_snapshot_failure_prevents_fresh_traffic(phase):
    """A transition cannot replace missing original settings with a new baseline."""
    with patch(MODULE + ".IPsecPolicyKeywords", return_value=NonCallableMock()), patch(MODULE + ".IPsecPolicyStateKeywords", return_value=NonCallableMock()) as state, patch(MODULE + ".IPsecPolicyTrafficKeywords") as traffic:
        keyword = IPsecPolicyCompatibilityKeywords(Mock())
        keyword.capture_original_configuration()
        state.return_value.capture_baseline.assert_called_once_with(exclusive=True)
        state.return_value.verify_configuration.side_effect = KeywordException("Original policy disappeared")
        with pytest.raises(KeywordException, match="Original policy disappeared"):
            keyword.verify_enforcement(Mock(), phase, "image", ("a", "b"))
        traffic.assert_not_called()
        assert state.return_value.capture_baseline.call_count == 1


def test_initial_discovery_waits_for_policy_agents():
    """A freshly applied operator must converge before strict node discovery."""
    policy = NonCallableMock()
    policy.get_eligible_nodes.return_value.get_node_names.return_value = ("compute-1", "compute-0")

    def discover_nodes():
        policy.wait_for_agents_ready.assert_called_once_with()
        return policy.get_eligible_nodes.return_value

    policy.get_eligible_nodes.side_effect = discover_nodes
    with patch(MODULE + ".IPsecPolicyKeywords", return_value=policy):
        keyword = IPsecPolicyCompatibilityKeywords(Mock())
        assert keyword.validate_inputs("26.03", "27.03", "image@sha256:" + "a" * 64) == ("compute-0", "compute-1")
