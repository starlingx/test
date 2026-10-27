"""Configured preparation with state-dependent release/capacity and failure evidence."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, NonCallableMagicMock, patch

import pytest

from config.usm.objects.usm_config import USMConfig
from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.upgrade.objects.software_deploy_precheck_output import SoftwareDeployPrecheckOutput
from keywords.cloud_platform.upgrade.objects.software_list_object import SoftwareListObject
from keywords.cloud_platform.upgrade.platform_upgrade_preparation_keywords import PlatformUpgradePreparationKeywords
from keywords.cloud_platform.upgrade.software_deploy_precheck_keywords import SoftwareDeployPrecheckKeywords

MODULE = "keywords.cloud_platform.upgrade.platform_upgrade_preparation_keywords"


class Filesystem:
    """Expose a filesystem whose size and state can change during polling."""

    def __init__(self, size=40, state="In-Use"):
        self.size, self.state = size, state

    def get_size(self):
        """Read current capacity."""
        return self.size

    def get_state(self):
        """Read current resize state."""
        return self.state


@pytest.fixture(autouse=True)
def loggers():
    """Keep framework logging independent of runner/lab configuration."""
    with patch("keywords.base_keyword.get_logger"), patch(f"{MODULE}.get_logger"), patch("framework.validation.validation.get_logger"):
        yield


@pytest.fixture
def preparation():
    """Build real preparation with a mutable release list and filesystem inventory."""
    helper = PlatformUpgradePreparationKeywords.__new__(PlatformUpgradePreparationKeywords)
    helper.config = USMConfig("config/usm/files/default.json5")
    helper.config.iso_path, helper.config.sig_path = "/staged/target.iso", "/staged/target.sig"
    helper.config.copy_from_remote = False
    helper.config.to_release_ids = ["starlingx-26.10.0"]
    helper.config.license_from_path, helper.config.license_server = "", ""
    entries = [SoftwareListObject("starlingx-26.03.0", "True", "deployed"), SoftwareListObject("starlingx-26.10.0", "True", "available")]
    helper.releases = NonCallableMagicMock()
    helper.releases.get_software_list.side_effect = lambda: SimpleNamespace(get_software_lists=lambda: list(entries), get_release_state_by_release_name=lambda key: next((r.get_state() for r in entries if r.get_release() == key), None))
    helper.usm = NonCallableMagicMock()
    helper.files = NonCallableMagicMock()
    helper.files.file_exists.return_value = True
    helper.license = NonCallableMagicMock()
    helper.precheck = NonCallableMagicMock()
    helper.ssh_connection = NonCallableMagicMock()
    helper.ssh_connection.get_return_code.return_value = 0
    helper.hosts = NonCallableMagicMock()
    helper.hosts.get_system_host_list.return_value.get_hosts.return_value = [SimpleNamespace(get_host_name=lambda: "controller-0", get_personality=lambda: "controller"), SimpleNamespace(get_host_name=lambda: "worker-0", get_personality=lambda: "worker")]
    filesystems = {("controller-0", "root"): Filesystem(), ("controller-0", "docker"): Filesystem(), ("worker-0", "root"): Filesystem()}
    helper.filesystems = NonCallableMagicMock()
    helper.filesystems.get_system_host_fs_list.side_effect = lambda host: SimpleNamespace(get_host_fs=lambda name: filesystems.get((host, name)))
    helper.filesystems.system_host_fs_modify.side_effect = lambda host, name, size: setattr(filesystems[host, name], "size", size)
    return helper, entries, filesystems


def test_prepared_lab_does_not_resize_or_reupload(preparation):
    """Repeated preparation preserves a sufficiently large lab and available target."""
    helper, _, _ = preparation
    helper.prepare("26.10")
    helper.prepare("26.10")
    helper.usm.upload_and_verify_release.assert_not_called()
    helper.filesystems.system_host_fs_modify.assert_not_called()
    helper.license.system_license_install.assert_not_called()
    helper.require_precheck("26.10")
    helper.precheck.precheck_release.assert_called_once_with("starlingx-26.10.0")


def test_only_small_required_filesystems_are_grown(preparation):
    """Grow undersized root/docker while preserving larger filesystems and worker geometry."""
    helper, _, filesystems = preparation
    filesystems["controller-0", "root"].size = 20
    filesystems["controller-0", "docker"].size = 60
    filesystems["worker-0", "root"].size = 30
    helper.prepare("26.10")
    assert [call.args for call in helper.filesystems.system_host_fs_modify.call_args_list] == [("controller-0", "root", 40), ("worker-0", "root", 40)]


@pytest.mark.parametrize("condition", ["missing", "failed", "unchanged-size"])
def test_filesystem_failure_cannot_pass(preparation, condition):
    """Require presence, successful state and increased size rather than any nonempty state."""
    helper, _, filesystems = preparation
    if condition == "missing":
        del filesystems["controller-0", "root"]
    elif condition == "failed":
        filesystems["controller-0", "root"].state = "Failed"
    else:
        filesystems["controller-0", "root"].size = 20
        helper.filesystems.system_host_fs_modify.side_effect = None

    # Execute the real polling predicate once and fail immediately for this local test.
    def check(predicate, expected, description, **kwargs):
        if predicate() != expected:
            raise TimeoutError(description)

    with patch(f"{MODULE}.validate_equals_with_retry", side_effect=check):
        with pytest.raises((KeywordException, TimeoutError)):
            helper.prepare("26.10")


def test_resize_waits_through_modifying(preparation):
    """A resized capacity is not sufficient while the filesystem remains Modifying."""
    helper, _, filesystems = preparation
    fs = filesystems["controller-0", "root"]
    fs.size, fs.state = 20, "Modifying"
    observations = []

    def check(predicate, expected, description, **kwargs):
        if "root" in description and "controller-0" in description:
            observations.append(predicate())
            fs.state = "In-Use"
        assert predicate() == expected

    with patch(f"{MODULE}.validate_equals_with_retry", side_effect=check):
        helper.prepare("26.10")
    assert observations == [False]


def test_controller_local_upload_and_release_verification(preparation):
    """Upload the configured pair, selecting the target ID rather than the first ID."""
    helper, entries, _ = preparation
    entries.pop()
    helper.config.to_release_ids = ["starlingx-25.09.0", "starlingx-26.10.0"]
    helper.usm.upload_and_verify_release.side_effect = lambda *args, **kwargs: entries.append(SoftwareListObject("starlingx-26.10.0", "True", "available"))
    helper.prepare("26.10")
    helper.usm.upload_and_verify_release.assert_called_once_with("/staged/target.iso", "/staged/target.sig", expected_release_id="starlingx-26.10.0", timeout=helper.config.get_upload_release_timeout_sec(), poll_interval=helper.config.get_upload_poll_interval_sec(), sudo=False)


@pytest.mark.parametrize("ids", [["starlingx-26.1.0"], ["starlingx-26.10.0", "other-26.10.0"]])
def test_missing_or_ambiguous_configured_target_fails_early(preparation, ids):
    """Reject wrong/ambiguous release IDs before growing filesystems or uploading."""
    helper, entries, _ = preparation
    entries.pop()
    helper.config.to_release_ids = ids
    with pytest.raises(ValueError):
        helper.prepare("26.10")
    helper.filesystems.system_host_fs_modify.assert_not_called()
    helper.usm.upload_and_verify_release.assert_not_called()


@pytest.mark.parametrize("state", ["deployed", "deploying", "unavailable"])
def test_existing_unusable_target_is_not_silently_reused(preparation, state):
    """An uploaded matching release must actually be available for a new deploy."""
    helper, entries, _ = preparation
    entries[-1].state = state
    with pytest.raises(KeywordException, match="expected available"):
        helper.prepare("26.10")
    helper.filesystems.system_host_fs_modify.assert_not_called()


def test_missing_local_or_remote_artifacts_fail_before_resize(preparation):
    """Do not start platform preparation with missing artifacts or incomplete credentials."""
    helper, entries, _ = preparation
    entries.pop()
    helper.files.file_exists.return_value = False
    with pytest.raises(KeywordException, match="missing"):
        helper.prepare("26.10")
    helper.config.copy_from_remote = True
    helper.config.remote_server, helper.config.remote_username, helper.config.remote_password = "source", "user", ""
    with pytest.raises(ValueError, match="source requires"):
        helper.prepare("26.10")
    helper.filesystems.system_host_fs_modify.assert_not_called()


def test_configured_local_license_is_uploaded_and_installed(preparation, tmp_path: Path):
    """Install the configured runner-local license while retaining prepared target behavior."""
    helper, _, _ = preparation
    license_path = tmp_path / "upgrade.lic"
    license_path.write_text("test license")
    helper.config.license_from_path = str(license_path)
    helper.config.license_to_path = "/home/sysadmin"
    helper.prepare("26.10")
    helper.files.upload_file.assert_called_once_with(str(license_path), "/home/sysadmin/upgrade.lic")
    helper.license.system_license_install.assert_called_once_with("/home/sysadmin/upgrade.lic")


@pytest.mark.parametrize("failure", [None, "transfer", "connect"])
def test_remote_sftp_transfer_closes_source_and_avoids_shell_passwords(preparation, failure):
    """Use the framework connection and SFTP, closing it on every transfer outcome."""
    helper, _, _ = preparation
    helper.config.remote_server, helper.config.remote_username, helper.config.remote_password = "source", "reader", "sentinel-secret"
    helper.config.dest_dir = "/staged"
    source = NonCallableMagicMock()
    source.connect.return_value = failure != "connect"
    source_sftp = MagicMock()
    source.get_sftp_client.return_value = source_sftp
    source_sftp.__enter__.return_value = source_sftp
    streams = []

    def source_stream(*args):
        stream = MagicMock()
        stream.__enter__.return_value = stream
        stream.read.side_effect = BytesIO(b"artifact").read
        streams.append(stream)
        return stream

    source_sftp.open.side_effect = source_stream
    source_sftp.stat.return_value.st_size = 8
    target = MagicMock()
    target.__enter__.return_value = target
    helper.ssh_connection.get_sftp_client.return_value = target
    if failure == "transfer":
        target.putfo.side_effect = OSError("injected transfer failure")
    with patch(f"{MODULE}.SSHConnection", return_value=source) as constructor:
        if failure:
            with pytest.raises((OSError, KeywordException)):
                helper._stage_remote_files("release")
        else:
            assert helper._stage_remote_files("release") == ("/staged/target.iso", "/staged/target.sig")
            assert [call.args[1] for call in target.putfo.call_args_list] == ["/staged/target.iso", "/staged/target.sig"]
        assert constructor.call_args.args[-1] == "sentinel-secret"
        source.close.assert_called_once()
        for stream in streams:
            stream.prefetch.assert_called_once_with(file_size=8, max_concurrent_requests=64)
            stream.__exit__.assert_called_once()
        if failure != "connect":
            source_sftp.__exit__.assert_called_once()
            target.__exit__.assert_called_once()
        assert "sentinel-secret" not in str(helper.ssh_connection.send.call_args_list)


@pytest.mark.parametrize("output,rc", [([], 0), (["authentication error"], 1), (["Health: [OK]"], 1), (["No alarms: [Fail]"], 0)])
def test_strict_precheck_rejects_empty_failed_and_nonzero(output, rc):
    """No health checks or a nonzero command status must never pass precheck."""
    helper = SoftwareDeployPrecheckKeywords.__new__(SoftwareDeployPrecheckKeywords)
    helper.ssh_connection = NonCallableMagicMock()
    helper.ssh_connection.get_return_code.return_value = rc
    with patch.object(helper, "_run_deploy_precheck", return_value=SoftwareDeployPrecheckOutput(output)):
        with pytest.raises(Exception):
            helper.precheck_release("starlingx-26.10.0")


def test_strict_precheck_uses_explicit_release_with_no_metapackages():
    """Run the release precheck even when normal metapackage selection is disabled."""
    helper = SoftwareDeployPrecheckKeywords.__new__(SoftwareDeployPrecheckKeywords)
    helper.ssh_connection = NonCallableMagicMock()
    helper.ssh_connection.get_return_code.return_value = 0
    output = SoftwareDeployPrecheckOutput(["Health: [OK]"])
    with patch.object(helper, "_run_deploy_precheck", return_value=output) as run:
        assert helper.precheck_release("starlingx-26.10.0") is output
        run.assert_called_once_with("starlingx-26.10.0")


def test_prepare_wires_remote_release_staging_into_upload(preparation):
    """The configured remote branch must upload the staged paths, not source paths."""
    helper, entries, _ = preparation
    entries.pop()
    helper.config.copy_from_remote = True
    helper.config.remote_server, helper.config.remote_username, helper.config.remote_password = "source", "reader", "sentinel-secret"
    helper.config.dest_dir = "/destination"
    helper.usm.upload_and_verify_release.side_effect = lambda *args, **kwargs: entries.append(SoftwareListObject("starlingx-26.10.0", "True", "available"))
    with patch.object(helper, "_stage_remote_files", return_value=("/destination/target.iso", "/destination/target.sig")) as stage:
        helper.prepare("26.10")
        stage.assert_called_once_with("release")
    helper.usm.upload_and_verify_release.assert_called_once_with("/destination/target.iso", "/destination/target.sig", expected_release_id="starlingx-26.10.0", timeout=helper.config.get_upload_release_timeout_sec(), poll_interval=helper.config.get_upload_poll_interval_sec(), sudo=False)
    helper.files.file_exists.assert_not_called()


def test_prepare_wires_configured_remote_license(preparation):
    """Stage and install the configured license without selecting a release source."""
    helper, _, _ = preparation
    helper.config.license_server, helper.config.license_username, helper.config.license_password = "licenses", "reader", "sentinel-secret"
    helper.config.license_from_path, helper.config.license_to_path = "/source/upgrade.lic", "/destination"
    with patch.object(helper, "_stage_remote_files", return_value=("/destination/upgrade.lic",)) as stage:
        helper.prepare("26.10")
        stage.assert_called_once_with("license")
    helper.license.system_license_install.assert_called_once_with("/destination/upgrade.lic")
    helper.files.upload_file.assert_not_called()
