"""Audit package resolution and shared lifecycle integration."""

from unittest.mock import NonCallableMagicMock, patch

import pytest

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.upgrade.audit_upgrade_setup_keywords import AuditUpgradeSetupKeywords

MODULE = "keywords.cloud_platform.upgrade.audit_upgrade_setup_keywords"


@pytest.fixture
def setup():
    """Build the adapter with checked lifecycle collaborators and private app config."""
    helper = AuditUpgradeSetupKeywords.__new__(AuditUpgradeSetupKeywords)
    helper.audit = NonCallableMagicMock()
    helper.audit.application_state.return_value = None
    helper.audit.command.return_value = "/bundled/auditd-26.03-42.tgz\n"
    helper.state = NonCallableMagicMock()
    helper.artifact, helper.version = None, None
    config = NonCallableMagicMock()
    config.get_base_application_path.return_value = "/bundled"
    config.get_auditd_test_options.return_value = {}
    with patch(f"{MODULE}.ConfigurationManager.get_app_config", return_value=config), patch("keywords.base_keyword.get_logger"):
        yield helper, config


def test_absent_app_resolves_and_validates_bundled_archive(setup):
    """Resolve a single bundled package and verify its metadata before state capture."""
    helper, _ = setup
    helper.capture("26.03")
    helper.state.validate_artifact.assert_called_once_with("/bundled/auditd-26.03-42.tgz", "26.03-42")
    helper.state.capture.assert_called_once_with(None)
    helper.prepare()
    helper.state.prepare.assert_called_once_with("/bundled/auditd-26.03-42.tgz", "26.03-42")


@pytest.mark.parametrize("status", ["uploaded", "applied"])
def test_existing_app_uses_exact_recovery_artifact(setup, status):
    """Preserve the exact existing app build and delegate preparation to shared state."""
    helper, _ = setup
    helper.audit.application_state.return_value = ("26.03-42", status)
    helper.capture("26.03")
    helper.state.capture.assert_called_once_with("/bundled/auditd-26.03-42.tgz")
    helper.audit.command.assert_not_called()
    helper.prepare()
    helper.state.prepare.assert_called_once_with("/bundled/auditd-26.03-42.tgz", "26.03-42")


def test_configured_recovery_archive_overrides_discovery(setup):
    """Use the caller's original archive without selecting another bundled build."""
    helper, config = setup
    config.get_auditd_test_options.return_value = {"baseline_artifact": "/recovery/original.tgz"}
    helper.audit.application_state.return_value = ("26.03-42", "applied")
    helper.capture("26.03")
    helper.state.capture.assert_called_once_with("/recovery/original.tgz")


def test_explicit_install_artifact_and_version(setup):
    """Permit exact custom package names, checked by the shared artifact validator."""
    helper, config = setup
    config.get_auditd_test_options.return_value = {"artifact": "/staged/custom.tgz", "version": "26.03-42"}
    helper.capture("26.03")
    helper.prepare()
    helper.audit.command.assert_not_called()
    helper.state.validate_artifact.assert_called_once_with("/staged/custom.tgz", "26.03-42")
    helper.state.prepare.assert_called_once_with("/staged/custom.tgz", "26.03-42")


@pytest.mark.parametrize("paths", ["", "/bundled/auditd-26.03-42.tgz\n/bundled/auditd-26.03-43.tgz"])
def test_missing_or_ambiguous_bundled_archive_fails(setup, paths):
    """Do not choose an arbitrary archive when the bundle is absent or ambiguous."""
    helper, _ = setup
    helper.audit.command.return_value = paths
    with pytest.raises(KeywordException, match="one bundled"):
        helper.capture("26.03")
    helper.state.capture.assert_not_called()
    helper.state.prepare.assert_not_called()


@pytest.mark.parametrize("options", [{"artifact": "/staged/app.tgz"}, {"version": "26.03-42"}, {"artifact": ""}, {"prepare": False}, {"unknown": True}, None, []])
def test_invalid_options_fail_before_capture(setup, options):
    """Reject incomplete and malformed setup configuration before mutation."""
    helper, config = setup
    config.get_auditd_test_options.return_value = options
    with pytest.raises(ValueError):
        helper.capture("26.03")
    helper.state.capture.assert_not_called()


def test_wrong_release_and_invalid_metadata_fail_before_mutation(setup):
    """Never install a target-release package as the starting-release baseline."""
    helper, _ = setup
    helper.audit.command.return_value = "/bundled/auditd-26.10-50.tgz"
    with pytest.raises(KeywordException, match="does not match"):
        helper.capture("26.03")
    helper.state.capture.assert_not_called()
    helper.audit.command.return_value = "/bundled/auditd-26.03-42.tgz"
    helper.state.validate_artifact.side_effect = KeywordException("bad metadata")
    with pytest.raises(KeywordException, match="bad metadata"):
        helper.capture("26.03")
    helper.state.capture.assert_not_called()
