from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords


class UpgradeRecoveryKeywords(BaseKeyword):
    """
    This class returns a system to its starting release after an upgrade test.

    A test that fails part-way through an upgrade leaves the platform mid-deploy and, if it removed
    an application first, leaves that application absent. Either state makes the lab unusable for
    the next run, and the failure the next run reports would point at the application rather than
    at the test that actually caused it.

    The recovery is deliberately narrow. Only the deploy states whose recovery is verified on
    hardware are acted on; anything else, a failed state in particular, is logged and left alone
    rather than driving untested recovery commands into a system that is already in trouble. It is
    also entirely best effort inside one try: a teardown that raises would replace the test's real
    failure with its own, and its first act is a command over an SSH session that may already be
    dead, for instance when the test was cut short during a host reboot.
    """

    RECOVERABLE_ROLLBACK_STATES = (
        "deploy-activate-rollback-pending",
        "deploy-activate-rollback-done",
        "deploy-host-rollback-done",
    )

    def __init__(self, ssh_connection: SSHConnection):
        """
        Instance of the class.

        Args:
            ssh_connection(SSHConnection): An instance of an SSH connection.

        """
        self.ssh_connection = ssh_connection
        self.deploy = SoftwareDeploySequenceKeywords(ssh_connection)
        self.health = ApplicationHealthKeywords(ssh_connection)
        self.app_apply = SystemApplicationApplyKeywords(ssh_connection)

    def restore_to_release(self, from_version: str, app_name: str = None, app_was_removed: bool = False) -> None:
        """
        Return the platform to its starting release, and an application if the test removed one.

        The host's running release is the ground truth for whether a restore is needed: 'software
        list' still reports the from-release as deployed until the deploy is completed, so it
        cannot tell "never upgraded" apart from "upgraded, awaiting rollback".

        A rollback that already started is resumed from where it reached rather than restarted,
        since 'deploy abort' is only valid from activate-done and re-issuing it from a mid-rollback
        state waits for a state that can never arrive, which hangs the teardown and hides the
        original failure.

        Args:
            from_version(str): the release the system should end on, for example "26.03".
            app_name(str): an application the test removed and that should be re-applied, or None.
            app_was_removed(bool): whether the test actually removed that application.

        """
        try:
            state = self.deploy.get_current_deploy_state()
            if from_version in self.deploy.get_running_release() and not state:
                get_logger().log_info(f"teardown: platform is on {from_version} with no deploy in progress")
            else:
                get_logger().log_info(f"teardown: restoring to {from_version}; current deploy state={state!r}")
                if state == "deploy-activate-done":
                    self.deploy.deploy_rollback()
                elif state in self.RECOVERABLE_ROLLBACK_STATES:
                    self.deploy.resume_partial_rollback()
                else:
                    get_logger().log_error(
                        f"teardown: deploy state {state!r} has no hardware-verified recovery path; "
                        f"leaving the deploy in place for inspection rather than guessing"
                    )

            if app_was_removed and app_name and not self.health.is_app_applied(app_name):
                get_logger().log_info(f"teardown: re-applying {app_name}, which this run removed")
                self.app_apply.system_application_apply(app_name)
        except Exception as recovery_error:  # noqa: BLE001 - teardown must not mask the real failure
            get_logger().log_error(f"teardown best-effort restore failed: {recovery_error}")
