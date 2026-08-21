import time

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords


class DcmanagerSwDeployStrategy(BaseKeyword):
    """
    This class executes sw-deploy-strategy commands
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): The SSH connection object used for executing commands.
        """
        self.ssh_connection = ssh_connection
        self.usm_config = ConfigurationManager.get_usm_config()

    def dcmanager_sw_deploy_strategy_create(self, subcloud_name: str = None, release: str = None, subcloud_group: str = None, with_delete: bool = False, delete_only: bool = False, rollback: bool = False, snapshot: bool = False, kube_upgrade: str = None, with_prestage: bool = False, sysadmin_password: str = None, cleanup: bool = False) -> str:
        """
        Runs dcmanager sw-deploy-strategy create command.

        Args:
            subcloud_name (str): The subcloud name.
            release (str): The software version to be deployed.
            subcloud_group (str): The subcloud group name.
            with_delete (bool): If true, adds parameter --with-delete
            delete_only (bool): If true, adds paramater --delete-only
            rollback (bool): If true, adds parameter --rollback
            snapshot (bool): If true, adds parameter --snapshot
            kube_upgrade (str): Target K8s version for combined P&K upgrade (e.g., 'v1.29.2').
            with_prestage (bool): If true, adds parameter --with-prestage (requires sysadmin_password).
            sysadmin_password (str): Sysadmin password for prestage (required when with_prestage is True).
            cleanup (bool): If true, adds parameter --cleanup. Completes/cleans up a
                sw-deploy that ended in a non-clean state (e.g. an aborted or failed
                deploy), deleting the leftover kube-upgrade and system-deploy entities.
                Not specific to auto-rollback.

        Returns:
            str: The joined stdout/stderr output of the create command.
        """
        command, target, is_group = self._build_sw_deploy_strategy_create_command(
            subcloud_name=subcloud_name,
            release=release,
            subcloud_group=subcloud_group,
            with_delete=with_delete,
            delete_only=delete_only,
            rollback=rollback,
            snapshot=snapshot,
            kube_upgrade=kube_upgrade,
            with_prestage=with_prestage,
            sysadmin_password=sysadmin_password,
            cleanup=cleanup,
        )

        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        self.wait_sw_deployment(subcloud=target, expected_status="initial", is_group=is_group)
        return "".join(output)

    def dcmanager_sw_deploy_strategy_create_with_error(self, subcloud_name: str = None, release: str = None, subcloud_group: str = None, with_delete: bool = False, delete_only: bool = False, rollback: bool = False, snapshot: bool = False, kube_upgrade: str = None, with_prestage: bool = False, sysadmin_password: str = None) -> str:
        """
        Runs dcmanager sw-deploy-strategy create expecting the command to be rejected.

        Used by negative tests where the create is expected to fail up front (e.g.
        mutually-exclusive options like --rollback with --with-delete, or an
        invalid release). Asserts a command-rejection return code instead of
        success and does not wait for the 'initial' state.

        Args: Same as dcmanager_sw_deploy_strategy_create.

        Returns:
            str: The joined stdout/stderr output of the rejected create command,
                for validation of the error message.
        """
        command, _, _ = self._build_sw_deploy_strategy_create_command(
            subcloud_name=subcloud_name,
            release=release,
            subcloud_group=subcloud_group,
            with_delete=with_delete,
            delete_only=delete_only,
            rollback=rollback,
            snapshot=snapshot,
            kube_upgrade=kube_upgrade,
            with_prestage=with_prestage,
            sysadmin_password=sysadmin_password,
        )

        output = self.ssh_connection.send(command)
        rejected = self.validate_cmd_rejection_return_code(self.ssh_connection)
        get_logger().log_info(f"sw-deploy-strategy create rejected as expected: {rejected}")
        return "".join(output)

    def _build_sw_deploy_strategy_create_command(self, subcloud_name: str = None, release: str = None, subcloud_group: str = None, with_delete: bool = False, delete_only: bool = False, rollback: bool = False, snapshot: bool = False, kube_upgrade: str = None, with_prestage: bool = False, sysadmin_password: str = None, cleanup: bool = False):
        """Build the dcmanager sw-deploy-strategy create command string and scope.

        Returns:
            tuple: (command, target, is_group) where command is the full
                source_openrc-wrapped CLI string, target is the subcloud/group
                name (or None for a system-wide strategy), and is_group indicates
                whether the target is a group.
        """
        release_id = f"--release-id {release}" if release else ""
        delete = "--with-delete" if with_delete else ""
        clean_up_delete = "--delete-only" if delete_only else ""
        rollback = "--rollback" if rollback else ""
        snapshot = "--snapshot" if snapshot else ""
        kube_upgrade_arg = f"--kube-upgrade {kube_upgrade}" if kube_upgrade else ""
        prestage_arg = "--with-prestage" if with_prestage else ""
        sysadmin_password_arg = f"--sysadmin-password {sysadmin_password}" if sysadmin_password else ""
        cleanup_arg = "--cleanup" if cleanup else ""

        # Resolve the strategy scope. dcmanager sw-deploy-strategy create takes an
        # OPTIONAL positional cloud_name: a single subcloud name targets that
        # subcloud, --group targets a group, and omitting both creates a
        # system-wide strategy across all eligible (managed/out-of-sync)
        # subclouds. Only one of these should be set; never emit the literal
        # string "None" as the positional argument.
        if subcloud_group:
            scope_arg = f"--group {subcloud_group}"
            target = subcloud_group
            is_group = True
        elif subcloud_name:
            scope_arg = subcloud_name
            target = subcloud_name
            is_group = False
        else:
            # System-wide strategy: no positional cloud_name, no --group.
            scope_arg = ""
            target = None
            is_group = True

        command = source_openrc(f"dcmanager sw-deploy-strategy create {scope_arg} {rollback} {snapshot} {release_id} {delete} {clean_up_delete} {kube_upgrade_arg} {prestage_arg} {sysadmin_password_arg} {cleanup_arg}")

        return command, target, is_group

    def dcmanager_sw_deploy_strategy_apply(self, target: str, is_group: bool = False, wait_completion: bool = True):
        """
        Runs dcmanager sw-deploy-strategy apply command.

        Args:
            target (str): The subcloud name or group name.
            is_group (bool): Whether the target is a group or individual subcloud.
            wait_completion (bool): If True, waits for the strategy step to reach 'complete',
                failing fast if it reaches 'failed'. If False, only sends the apply command and
                validates the return code, letting the caller poll the resulting state
                (e.g. via DcmanagerStrategyStepKeywords.wait_for_strategy_step_state) — useful when
                a 'failed' outcome is expected rather than an error condition.
        """
        command = source_openrc("dcmanager sw-deploy-strategy apply")

        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

        if not wait_completion:
            return

        deployment_timeout = self.usm_config.get_deployment_timeout_sec()
        poll_interval = self.usm_config.get_upload_poll_interval_sec()
        self.wait_sw_deployment(
            subcloud=target,
            expected_status="complete",
            timeout=deployment_timeout,
            check_interval=poll_interval,
            is_group=is_group,
        )

    def dcmanager_sw_deploy_strategy_abort(self) -> None:
        """Runs dcmanager sw-deploy-strategy abort command.

        Only issues the abort request and validates that the command was
        accepted (success return code). It does NOT wait for the strategy to
        settle - call wait_sw_deploy_strategy_abort() afterwards to poll the
        strategy step until it reaches a terminal post-abort state.

        Raises:
            AssertionError: If the abort command does not return success.
        """
        get_logger().log_info("Aborting sw-deploy-strategy")
        command = source_openrc("dcmanager sw-deploy-strategy abort")
        self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)

    def wait_sw_deploy_strategy_abort(
        self,
        subcloud: str,
        timeout: int = 1200,
        check_interval: int = 30,
        is_group: bool = False,
    ) -> str:
        """Wait for sw-deploy-strategy abort to settle.

        Polls strategy-step state until it reaches a terminal state, then returns
        that state for the caller to assert on. Terminal states considered here:

            - 'aborted': the step was cancelled by the abort (typical for
              queued/not-yet-executing subclouds).
            - 'failed': the step ended in failure.
            - 'complete': a step that was already executing when the abort was
              issued is NOT interrupted mid-step and can run to completion (the
              dcmanager abort cancels queued subclouds, not the in-flight VIM
              strategy). This is a valid, expected outcome for the executing
              subcloud, so it is treated as terminal here. Callers that require
              the abort to have actually cancelled the step should assert on the
              returned state rather than relying on this method to reject
              'complete'.

        Args:
            subcloud (str): Subcloud name or group to monitor.
            timeout (int): Maximum wait time in seconds (default 1200s / 20min).
            check_interval (int): Polling interval in seconds.
            is_group (bool): Whether the target is a group or individual subcloud.

        Returns:
            str: The terminal state reached by the strategy step.
        """
        terminal_states = ["aborted", "failed", "complete"]

        def check_abort_state() -> bool:
            if is_group:
                strategy_steps = DcmanagerStrategyStepKeywords(self.ssh_connection).get_dcmanager_strategy_step_list()
                steps = strategy_steps.get_dcmanager_strategy_step_list()
                if not steps:
                    return False
                return all(step.get_state() in terminal_states for step in steps)
            else:
                state = DcmanagerStrategyStepKeywords(self.ssh_connection).get_dcmanager_strategy_step_show(subcloud).get_dcmanager_strategy_step_show().get_state()
                get_logger().log_info(f"Strategy step state for {subcloud}: {state}")
                return state in terminal_states

        validate_equals_with_retry(
            function_to_execute=check_abort_state,
            expected_value=True,
            validation_description=f"Waiting for sw-deploy-strategy abort to complete for {subcloud}.",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )

        # Return the final state
        if is_group:
            steps = DcmanagerStrategyStepKeywords(self.ssh_connection).get_dcmanager_strategy_step_list().get_dcmanager_strategy_step_list()
            return steps[0].get_state() if steps else "unknown"
        else:
            return DcmanagerStrategyStepKeywords(self.ssh_connection).get_dcmanager_strategy_step_show(subcloud).get_dcmanager_strategy_step_show().get_state()

    def check_sw_deploy_strategy_delete_output(self):
        """
        Verifies dcmanager sw-deploy-strategy delete output.
        """
        command = source_openrc("dcmanager sw-deploy-strategy delete")

        output = self.ssh_connection.send(command)
        if "Strategy with type sw-deploy doesn't exist." in "".join(output):
            get_logger().log_info("No strategy to be deleted, moving on...")
            return True
        elif "Strategy in state deleting cannot be deleted" in "".join(output):
            return False

    def dcmanager_sw_deploy_strategy_delete(self):
        """
        Starts sw-deploy-strategy deletion process if there is a strategy in progress and waits for its deletion.
        """
        validate_equals_with_retry(function_to_execute=self.check_sw_deploy_strategy_delete_output, expected_value=True, validation_description="Waits for strategy deletion", timeout=240, polling_sleep_time=10)

    def wait_sw_deployment(
        self,
        subcloud: str,
        expected_status: str,
        check_interval: int = 30,
        timeout: int = 240,
        is_group: bool = False,
    ) -> None:
        """
        Waits for check_sw_deployment method to return True.
        """

        def check_sw_deployment() -> str:
            """
            Checks if the sw deployment operation has been completed, either 'create' or 'apply'.

            Returns:
                str: Expected status for sw deployment.
            """
            if is_group:
                # For subcloud groups, use dcmanager strategy-step list
                strategy_steps = DcmanagerStrategyStepKeywords(self.ssh_connection).get_dcmanager_strategy_step_list()
                steps = strategy_steps.get_dcmanager_strategy_step_list()
                if not steps:
                    return "unknown"
                # Check if all subclouds have the expected state
                for step in steps:
                    if step.get_state() != expected_status:
                        return step.get_state()  # Return the first non-matching state
                return expected_status  # All subclouds have expected state
            else:
                # For individual subclouds, use dcmanager strategy-step show <subcloud_name>
                sw_deployment_status = DcmanagerStrategyStepKeywords(self.ssh_connection).get_dcmanager_strategy_step_show(subcloud).get_dcmanager_strategy_step_show().get_state()
                return sw_deployment_status

        validate_equals_with_retry(function_to_execute=check_sw_deployment, expected_value=expected_status, validation_description=f"Waiting for sw_deployment_status {expected_status}.", timeout=timeout, polling_sleep_time=check_interval, failure_values=["failed"])

    def dc_manager_sw_deploy_strategy_create_apply_delete(self, subcloud_name: str = None, release: str = None, subcloud_group: str = None, with_delete: bool = False, delete_only: bool = False, rollback: bool = False, snapshot: bool = False, kube_upgrade: str = None):
        """
        Runs dcmanager sw-deploy-strategy create / apply / delete commands.

        Args:
            subcloud_name (str): The subcloud name.
            release (str): The software version to be deployed.
            subcloud_group (str): The subcloud group name.
            with_delete (bool): If true, adds parameter --with-delete
            delete_only (bool): If true, adds paramater --delete-only
            rollback (bool): If true, adds parameter --rollback
            snapshot (bool): If true, adds parameter --snapshot
            kube_upgrade (str): Target K8s version for combined P&K upgrade (e.g., 'v1.29.2').
        """
        target = subcloud_group if subcloud_group else subcloud_name
        is_group = bool(subcloud_group)
        get_logger().log_test_case_step(f"Create the sw-deploy strategy for {target} with {release}")
        self.dcmanager_sw_deploy_strategy_create(subcloud_name=subcloud_name, release=release, subcloud_group=subcloud_group, with_delete=with_delete, delete_only=delete_only, rollback=rollback, snapshot=snapshot, kube_upgrade=kube_upgrade)
        get_logger().log_test_case_step("Apply the sw-deploy strategy")
        self.dcmanager_sw_deploy_strategy_apply(target, is_group=is_group)
        time.sleep(120)
        get_logger().log_test_case_step("Delete the sw-deploy strategy")
        self.dcmanager_sw_deploy_strategy_delete()
