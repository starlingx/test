"""Shared configured preparation for platform upgrade compatibility tests."""

from pathlib import Path, PurePosixPath
from shlex import quote

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.host.system_host_fs_keywords import SystemHostFSKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.license.system_license_keywords import SystemLicenseKeywords
from keywords.cloud_platform.upgrade.software_deploy_precheck_keywords import SoftwareDeployPrecheckKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords
from keywords.files.file_keywords import FileKeywords


class PlatformUpgradePreparationKeywords(BaseKeyword):
    """Prepare configured artifacts and capacity without choosing a lab or release."""

    MINIMUM_FS_GIB = 40

    def __init__(self, ssh_connection: SSHConnection) -> None:
        self.ssh_connection = ssh_connection
        self.config = ConfigurationManager.get_usm_config()
        self.releases = SoftwareListKeywords(ssh_connection)
        self.usm = USMKeywords(ssh_connection)
        self.files = FileKeywords(ssh_connection)
        self.hosts = SystemHostListKeywords(ssh_connection)
        self.filesystems = SystemHostFSKeywords(ssh_connection)
        self.license = SystemLicenseKeywords(ssh_connection)
        self.precheck = SoftwareDeployPrecheckKeywords(ssh_connection)

    @staticmethod
    def matches_version(release_id: str, version: str) -> bool:
        """Match a short platform version at its release boundary.

        Args:
            release_id (str): Full platform release ID.
            version (str): Short target version.

        Returns:
            bool: Whether the release belongs to that version.
        """
        suffix = release_id.rsplit("-", 1)[-1]
        return suffix == version or suffix.startswith(f"{version}.")

    def available_release(self, version: str) -> str | None:
        """Find an unambiguous available target, rejecting an already deployed target.

        Args:
            version (str): Target platform version.

        Returns:
            str | None: Available release ID, or None when upload is needed.
        """
        matches = [entry for entry in self.releases.get_software_list().get_software_lists() if self.matches_version(entry.get_release(), version)]
        if len(matches) > 1:
            raise KeywordException(f"Multiple uploaded releases match {version}; choose an unambiguous platform target")
        if not matches:
            return None
        entry = matches[0]
        if entry.get_state() != "available":
            raise KeywordException(f"Target {entry.get_release()} is {entry.get_state()}, expected available before a new upgrade")
        return entry.get_release()

    def prepare(self, version: str) -> None:
        """Grow required filesystems, install a configured license and upload the target.

        Existing available releases and sufficient filesystems are left alone.
        Credentials and source locations come exclusively from USM configuration.
        These platform preparation changes persist for subsequent runs.

        Args:
            version (str): Target short release from compatibility configuration.
        """
        existing = self.available_release(version)
        expected = None
        if existing is None:
            candidates = [entry for entry in self.config.get_to_release_ids() if self.matches_version(entry, version)]
            if len(candidates) != 1:
                raise ValueError(f"USM to_release_ids must contain exactly one platform release matching {version}")
            expected = candidates[0]
            paths = (self.config.get_iso_path(), self.config.get_sig_path())
            if not all(paths) or paths[0] == paths[1]:
                raise ValueError("USM iso_path and sig_path must identify distinct source files")
            for path in paths:
                self._absolute_path(path)
            if self.config.get_copy_from_remote():
                if not all((self.config.get_remote_server(), self.config.get_remote_username(), self.config.get_remote_password())):
                    raise ValueError("Remote release source requires configured server, username and password")
                self._absolute_path(self.config.get_dest_dir())
                if PurePosixPath(paths[0]).name == PurePosixPath(paths[1]).name:
                    raise ValueError("ISO and signature must have distinct staging names")
            elif not all(self.files.file_exists(path) for path in paths):
                raise KeywordException("Configured controller-local ISO or signature is missing")
        self._validate_license_source()
        self._ensure_filesystems()
        self._install_license()
        if existing is not None:
            get_logger().log_info(f"Target {existing} is already available; skipping load upload")
            return
        if self.config.get_copy_from_remote():
            iso, signature = self._stage_remote_files("release")
        else:
            iso, signature = self.config.get_iso_path(), self.config.get_sig_path()
        self.usm.upload_and_verify_release(
            quote(iso),
            quote(signature),
            expected_release_id=expected,
            timeout=self.config.get_upload_release_timeout_sec(),
            poll_interval=self.config.get_upload_poll_interval_sec(),
            sudo=False,
        )
        if self.available_release(version) != expected:
            raise KeywordException("Uploaded release does not match the configured platform target")

    def require_precheck(self, version: str) -> None:
        """Check the prepared system against the exact target release before deploy-start.

        Args:
            version (str): Target short platform version.
        """
        release = self.available_release(version)
        if release is None:
            raise KeywordException(f"Target {version} is not uploaded")
        self.precheck.precheck_release(release)

    def _ensure_filesystems(self) -> None:
        """Grow root on each host and docker on controllers, verifying size and state."""
        hosts = self.hosts.get_system_host_list().get_hosts()
        if not hosts:
            raise KeywordException("No hosts found for platform preparation")
        for host in hosts:
            hostname = host.get_host_name()
            names = ("root", "docker") if host.get_personality() == "controller" else ("root",)
            for name in names:
                fs = self.filesystems.get_system_host_fs_list(hostname).get_host_fs(name)
                if fs is None:
                    raise KeywordException(f"Required {name} filesystem missing on {hostname}")
                if fs.get_size() < self.MINIMUM_FS_GIB:
                    self.filesystems.system_host_fs_modify(hostname, name, self.MINIMUM_FS_GIB)
                validate_equals_with_retry(
                    lambda: self._filesystem_ready(hostname, name),
                    True,
                    f"{hostname}: {name} capacity is ready",
                    timeout=300,
                    polling_sleep_time=15,
                )

    def _filesystem_ready(self, hostname: str, name: str) -> bool:
        """Observe both the resulting capacity and a successful steady state.

        Args:
            hostname (str): Inventory node.
            name (str): Required filesystem.

        Returns:
            bool: Whether capacity and state are ready.
        """
        fs = self.filesystems.get_system_host_fs_list(hostname).get_host_fs(name)
        if fs is None:
            raise KeywordException(f"Required {name} filesystem disappeared on {hostname}")
        state = fs.get_state().lower()
        if "fail" in state or "error" in state:
            raise KeywordException(f"{hostname}: {name} filesystem resize failed: {fs.get_state()}")
        return fs.get_size() >= self.MINIMUM_FS_GIB and state == "in-use"

    @staticmethod
    def _absolute_path(value: str) -> None:
        """Reject missing, relative or multiline artifact locations.

        Args:
            value (str): Configured POSIX path.
        """
        if not isinstance(value, str) or not value or not PurePosixPath(value).is_absolute() or any(char in value for char in "\n\r"):
            raise ValueError("Upgrade artifact paths must be nonempty absolute paths")

    def _validate_license_source(self) -> None:
        """Validate optional license configuration before platform mutations."""
        source = self.config.get_license_from_path()
        if not source:
            if self.config.get_license_server():
                raise ValueError("license_from_path is required with a configured license server")
            return
        self._absolute_path(source)
        self._absolute_path(self.config.get_license_to_path())
        if self.config.get_license_server():
            if not all((self.config.get_license_username(), self.config.get_license_password())):
                raise ValueError("License server requires configured username and password")
        elif not Path(source).is_file():
            raise ValueError("Configured runner-local license file is missing")

    def _install_license(self) -> None:
        """Install a configured license, otherwise leave the existing license for precheck."""
        source = self.config.get_license_from_path()
        if not source:
            get_logger().log_info("No upgrade license configured; release precheck will validate the installed license")
            return
        if self.config.get_license_server():
            destination = self._stage_remote_files("license")[0]
        else:
            directory = self.config.get_license_to_path()
            self._make_directory(directory)
            destination = str(PurePosixPath(directory) / PurePosixPath(source).name)
            self.files.upload_file(source, destination)
        self.license.system_license_install(quote(destination))

    def _make_directory(self, path: str) -> None:
        """Create a quoted staging directory and check the command status.

        Args:
            path (str): Controller-local directory.
        """
        self._absolute_path(path)
        self.ssh_connection.send(f"mkdir -p -- {quote(path)}")
        self.validate_success_return_code(self.ssh_connection)

    def _stage_remote_files(self, kind: str) -> tuple[str, ...]:
        """Stream configured remote artifacts through framework SFTP without shell secrets.

        Source servers must be reachable by the runner. Passwords are read inside
        this operation, never passed to keyword logging or command arguments.

        Args:
            kind (str): Release or license source configuration to use.

        Returns:
            tuple[str, ...]: Controller-local staged file paths.
        """
        if kind == "release":
            server, username, password = self.config.get_remote_server(), self.config.get_remote_username(), self.config.get_remote_password()
            paths, directory = (self.config.get_iso_path(), self.config.get_sig_path()), self.config.get_dest_dir()
        elif kind == "license":
            server, username, password = self.config.get_license_server(), self.config.get_license_username(), self.config.get_license_password()
            paths, directory = (self.config.get_license_from_path(),), self.config.get_license_to_path()
        else:
            raise ValueError("Unknown configured artifact source")
        self._make_directory(directory)
        source = SSHConnection("upgrade-artifacts", server, username, password)
        try:
            if not source.connect(allow_agent=False, look_for_keys=False):
                raise KeywordException("Could not connect to configured upgrade artifact source")
            with source.get_sftp_client() as source_sftp, self.ssh_connection.get_sftp_client() as target_sftp:
                result = []
                for path in paths:
                    destination = str(PurePosixPath(directory) / PurePosixPath(path).name)
                    size = source_sftp.stat(path).st_size
                    with source_sftp.open(path, "rb") as stream:
                        # Pipeline reads across high-latency runner/source links instead
                        # of waiting one round trip for every 32 KiB block.
                        stream.prefetch(file_size=size, max_concurrent_requests=64)
                        target_sftp.putfo(stream, destination, file_size=size)
                    result.append(destination)
                return tuple(result)
        finally:
            source.close()
