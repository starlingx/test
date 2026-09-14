from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
from keywords.cloud_platform.upgrade.software_deploy_show_keywords import SoftwareDeployShowKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords


class SoftwareDeploySequenceKeywords(BaseKeyword):
    """
    This class contains keywords for driving the USM software deploy state machine.

    The individual verbs live in USMKeywords; what this class adds is the sequencing the platform
    requires between them, the waits that must succeed before the next verb is issued, and the
    reads that tell a caller where a deploy actually is. A platform upgrade and its rollback are
    multi-step sequences whose steps are rejected out of order, so they are kept together here
    rather than left for each caller to reassemble.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Instance of the class.

        Args:
            ssh_connection(SSHConnection): An instance of an SSH connection.

        """
        self.ssh_connection = ssh_connection
        self.usm = USMKeywords(ssh_connection)
        self.software_list = SoftwareListKeywords(ssh_connection)
        self.deploy_show = SoftwareDeployShowKeywords(ssh_connection)
        self.system_show = SystemShowKeywords(ssh_connection)
        self.host_lock = SystemHostLockKeywords(ssh_connection)
        self.host_swact = SystemHostSwactKeywords(ssh_connection)
        self.alarms = AlarmListKeywords(ssh_connection)

    def get_current_deploy_state(self) -> str:
        """
        Return the current 'software deploy show' state, or "" when no deploy exists.

        When no deploy is in progress the show table is empty, so the unset object is guarded
        against: SoftwareDeployShowOutput only sets its deploy-show object when a row exists.

        Returns:
            str: the deploy state, for example "deploy-activate-done", or "" when there is no
                deploy in progress.

        """
        show = self.deploy_show.get_software_deploy_show()
        if not show.get_software_deploy_show_details():
            return ""
        # This is a plain getter on the already-parsed output object, not a second CLI call,
        # despite sharing a name with the keyword method above.
        return show.get_software_deploy_show().get_state()

    def require_deploy_state(self, expected_state: str) -> None:
        """
        Wait for a deploy state and fail loudly when it is not reached.

        Named to distinguish it from USMKeywords.wait_for_deploy_state, which it wraps: that one
        returns False on timeout and also returns False as soon as the observed state contains
        "failed", and never raises. An unchecked call therefore lets a failed deploy proceed to the
        next phase - locking hosts, deploying them, activating - and lets a teardown skip its
        recovery branches, both of which hide the real failure. This converts that False into an
        exception carrying the state that was actually observed.

        Args:
            expected_state(str): the deploy state to wait for, for example "deploy-start-done".

        Raises:
            KeywordException: when the expected state is not reached, by timeout or by the deploy
                entering a failed state.

        """
        if not self.usm.wait_for_deploy_state(expected_state):
            observed = self.get_current_deploy_state()
            raise KeywordException(
                f"Deploy did not reach {expected_state!r}; observed state={observed!r}. "
                f"Refusing to continue - the deploy either failed or timed out."
            )

    def get_release_id_for_version(self, version: str) -> str:
        """
        Return the full platform release ID whose name contains the given short version.

        Short platform versions such as "26.10" are what 'system application-show' and the
        deployed release name are matched against, but USM requires the full release ID as
        reported by 'software list', for example "starlingx-26.10.0". Passing a short version to
        'software deploy start' is rejected with "Software release version corresponding to the
        specified release does not exist". This resolves one to the other from the live system
        rather than hardcoding a naming prefix, so it works whatever the release naming is.

        Args:
            version(str): short platform version, for example "26.10".

        Returns:
            str: the matching full release ID.

        Raises:
            KeywordException: when no uploaded release matches, which means the target load was
                never uploaded; or when several match and none matches exactly, since deploying
                whichever was listed first could upgrade the system to the wrong release.

        """
        releases = [entry.get_release() for entry in self.software_list.get_software_list().get_software_lists()]
        matches = [release for release in releases if version in release]
        if not matches:
            raise KeywordException(
                f"No uploaded release matches version {version!r}; available releases: "
                f"{releases}. Upload the target load ('software upload <iso> <sig>') first."
            )
        if len(matches) > 1:
            # A short version can be a substring of more than one release, so prefer a release
            # whose version segment is exactly the requested value before giving up.
            exact = [release for release in matches if release.rsplit("-", 1)[-1] == version]
            if len(exact) == 1:
                return exact[0]
            raise KeywordException(
                f"Version {version!r} matches several uploaded releases: {matches}. Use a more "
                f"specific version so the target release is unambiguous."
            )
        return matches[0]

    def get_running_release(self) -> str:
        """
        Return the platform release the host is actually running.

        This is the host's own view, via 'system show' software_version, and it is the ground
        truth for whether an upgrade took effect. After 'software deploy activate' the host runs
        the new release even though 'software list' still reports the old release as "deployed"
        and the new one merely as "deploying"; those states only settle on 'software deploy
        complete', which an upgrade-then-rollback run deliberately never issues.

        Returns:
            str: the running platform version, for example "26.10".

        """
        return self.system_show.system_show().get_system_show_object().get_software_version()

    def deploy_host_guarded(self, host: str, rollback: bool = False) -> None:
        """
        Lock a host, deploy or roll it back, and unlock it even when that fails.

        Without the unlock in a finally, a failure part-way through the deploy leaves the host
        locked, which wedges the system - on a single-controller system it takes the whole
        platform out. The host is also swacted away from first when it is the active controller,
        since the platform refuses to lock an active controller.

        Args:
            host(str): the host to deploy or roll back.
            rollback(bool): when True the host is rolled back to the from-release instead of
                deployed to the target release.

        """
        self.host_swact.swact_if_active(host)
        self.host_lock.lock_host(host)
        try:
            if rollback:
                self.usm.software_deploy_host_rollback(host, sudo=False)
            else:
                self.usm.software_deploy_host(host, sudo=False)
        finally:
            self.host_lock.unlock_host(host)

    def deploy_upgrade(self, version: str, leave_at_activate_done: bool = False) -> None:
        """
        Drive the deploy state machine to upgrade the platform to the given release.

        The sequence, and the ordering rules the platform enforces rather than merely prefers:

          deploy start -> deploy-start-done
          per host in the platform's own deploy order, which is standby controller first because
            deploying the active one first is rejected: swact away if active, lock, deploy host,
            unlock -> deploy-host-done
          deploy activate -> deploy-activate-done
          deploy complete -> deploy-completed, only when no rollback will follow

        Every wait raises when its state is not reached, so a failed deploy stops here instead of
        continuing to lock hosts and activate.

        'deploy complete' is skipped when a rollback will follow, because the rollback runs from
        deploy-activate-done by way of 'deploy abort' and completing the deploy first would take
        that route away. It is issued otherwise, since leaving a deploy open keeps its alarms
        raised and blocks later operations.

        Args:
            version(str): short platform version of the target release, for example "26.10",
                resolved here to the full release ID USM requires.
            leave_at_activate_done(bool): when True the deploy is left at deploy-activate-done so
                a rollback can run from there; when False the deploy is completed.

        Raises:
            KeywordException: when an alarm is present that would make 'deploy start' refuse, so
                the cause is named rather than surfacing as an opaque non-zero return code.

        """
        self._require_no_blocking_alarms()
        self.usm.deploy_start(self.get_release_id_for_version(version), sudo=False)
        self.require_deploy_state("deploy-start-done")
        for host in self.usm.deploy_host_upgrade_order():
            self.deploy_host_guarded(host, rollback=False)
        self.require_deploy_state("deploy-host-done")
        self.usm.software_deploy_activate(sudo=False)
        self.require_deploy_state("deploy-activate-done")
        if not leave_at_activate_done:
            self.usm.software_deploy_complete(sudo=False)
            self.require_deploy_state("deploy-completed")

    def _require_no_blocking_alarms(self) -> None:
        """
        Fail with the offending alarms named when an alarm would block 'deploy start'.

        'software deploy start' runs its own health check and refuses on any active alarm, reporting
        only "No alarms: [Fail]" and a count. Since the verb returns a non-zero code rather than
        raising something descriptive, a caller sees an assertion on a return code and has to go
        and read the deploy log to find out what was actually wrong. Reading the alarms first turns
        that into a message naming them.

        This is a precondition check, not a workaround: an alarm at this point means the system is
        not in a state the platform will upgrade, and that is worth reporting precisely.

        Raises:
            KeywordException: when any alarm is active.

        """
        alarms = self.alarms.alarm_list()
        if alarms:
            described = ", ".join(
                f"{alarm.get_alarm_id()} ({alarm.get_entity_id()})" for alarm in alarms
            )
            raise KeywordException(
                f"Refusing to start a deploy with {len(alarms)} active alarm(s): {described}. "
                f"'software deploy start' rejects any alarm, so this would fail with only a count "
                f"reported. Clear the alarms, or if they are test artifacts, remove whatever raised "
                f"them before upgrading."
            )

    def deploy_rollback(self) -> None:
        """
        Roll the platform back to the from-release after the deploy was activated.

        A post-activate rollback is not one command. 'deploy activate-rollback' on its own is
        rejected - it is valid only from activate-rollback-pending - so the verified sequence is:

          deploy abort -> deploy-activate-rollback-pending, which also flips From and To release
          deploy activate-rollback -> deploy-activate-rollback-done
          per host, standby first, swacting away from the active one before locking it:
            lock, host-rollback, unlock -> deploy-host-rollback-done
          deploy delete, to finalise

        """
        self.usm.software_deploy_abort(sudo=False)
        self.require_deploy_state("deploy-activate-rollback-pending")
        self.usm.software_deploy_activate_rollback(sudo=False)
        self.require_deploy_state("deploy-activate-rollback-done")
        for host in self.usm.deploy_host_upgrade_order():
            self.deploy_host_guarded(host, rollback=True)
        self.require_deploy_state("deploy-host-rollback-done")
        self.usm.software_deploy_delete(sudo=False)

    def resume_partial_rollback(self) -> None:
        """
        Resume a rollback that already started, from whatever state it reached.

        A teardown recovering a run that failed part-way through its rollback must not restart
        from 'deploy abort': abort is only valid from activate-done, so re-issuing it from a
        mid-rollback state fails, and waiting for activate-rollback-pending from there waits for a
        state that can never arrive, which hangs the teardown and hides the original failure.

        Each step is therefore entered only from the state that precedes it. After a wait
        succeeds the reached state is known, so it is assigned rather than re-read: the wait raises
        if the state was not reached, so re-reading could only return the same value at the cost
        of another CLI call.

        Only the states whose recovery is verified on hardware are acted on. Anything else,
        notably a failed state, is left alone for a human rather than driving untested recovery
        commands into a system that is already in trouble.

        """
        state = self.get_current_deploy_state()
        if state == "deploy-activate-rollback-pending":
            self.usm.software_deploy_activate_rollback(sudo=False)
            self.require_deploy_state("deploy-activate-rollback-done")
            state = "deploy-activate-rollback-done"
        if state == "deploy-activate-rollback-done":
            for host in self.usm.deploy_host_upgrade_order():
                self.deploy_host_guarded(host, rollback=True)
            self.require_deploy_state("deploy-host-rollback-done")
            state = "deploy-host-rollback-done"
        if state == "deploy-host-rollback-done":
            self.usm.software_deploy_delete(sudo=False)
