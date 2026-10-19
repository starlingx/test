"""State-restoring audit preparation for platform compatibility tests."""

from pathlib import PurePosixPath
from shlex import quote

from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.applications.auditd_keywords import AuditdKeywords
from keywords.cloud_platform.applications.auditd_state import AuditdBaseline, AuditdState


class AuditUpgradeSetupKeywords(BaseKeyword):
    """Resolve baseline artifacts and reuse the shared audit-state lifecycle."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        self.audit = AuditdKeywords(ssh_connection)
        self.state = AuditdState(self.audit)
        self.artifact = None
        self.version = None

    def capture(self, release: str) -> AuditdBaseline:
        """Capture recoverable state and resolve the baseline package before mutations.

        Args:
            release (str): Installed platform release.

        Returns:
            AuditdBaseline: Original audit/kernel/controller state.
        """
        config = ConfigurationManager.get_app_config()
        options = config.get_auditd_test_options()
        if not isinstance(options, dict):
            raise ValueError("auditd_test_options must be a mapping")
        allowed = {"artifact", "version", "baseline_artifact"}
        if set(options) - allowed:
            raise ValueError("Unknown auditd_test_options for compatibility setup")
        for key in allowed:
            if key in options and (not isinstance(options[key], str) or not options[key].strip()):
                raise ValueError(f"auditd_test_options.{key} must be a nonempty string")
        application = self.audit.application_state()
        baseline_artifact = options.get("baseline_artifact")
        if application:
            self.version = application[0]
            self.artifact = baseline_artifact or str(PurePosixPath(config.get_base_application_path()) / f"auditd-{self.version}.tgz")
            baseline_artifact = self.artifact
        else:
            self.artifact, self.version = options.get("artifact"), options.get("version")
            if bool(self.artifact) != bool(self.version):
                raise ValueError("Provide both auditd artifact and version, or neither to use the bundled package")
            if not self.artifact:
                base = config.get_base_application_path()
                if not PurePosixPath(base).is_absolute():
                    raise ValueError("base_application_path must be absolute")
                paths = self.audit.command(f"find {quote(base)} -maxdepth 1 -type f -name 'auditd-*.tgz'").splitlines()
                if len(paths) != 1:
                    raise KeywordException("Expected one bundled auditd archive; configure artifact/version to select an exact package")
                self.artifact = paths[0]
                self.version = PurePosixPath(self.artifact).name.removeprefix("auditd-").removesuffix(".tgz")
            self.state.validate_artifact(self.artifact, self.version)
        if not self.version.startswith(f"{release}-"):
            raise KeywordException(f"Audit baseline package version {self.version} does not match installed platform {release}")
        return self.state.capture(baseline_artifact)

    def prepare(self) -> None:
        """Enable audit, reboot mismatching hosts and upload/apply before deploy-start."""
        self.state.prepare(self.artifact, self.version)

    def restore(self) -> None:
        """Restore the original audit baseline after platform recovery has completed."""
        self.state.restore()
