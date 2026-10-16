"""Standard-lab-correct platform upgrade and rollback drivers.

These drivers exist because the shared SoftwareDeploySequenceKeywords.deploy_upgrade /
deploy_rollback use the UPGRADE host order (controllers by live active/standby role) for both
directions. On a Standard lab (two controllers plus workers) that order is wrong for a rollback:
the platform rejects 'software deploy host-rollback' out of order with "does not satisfy the right
order of deployment should be <host>", which surfaces only as a non-zero return code and fails the
run. It also issues the per-controller swact before the standby has finished coming up after its
deploy/reboot, so the swact is rejected. These drivers fix both: they roll hosts back in the
platform's documented order (workers/storage, then controllers by NAME) and wait for the standby to
be operationally enabled before each swact-sensitive controller step, reusing the shared deploy
verbs, guarded per-host step and state waits otherwise. An AIO-DX lab with no workers does not
expose the ordering issue, which is why the shared methods have not needed the distinction.

Generic: any Standard-lab upgrade/rollback test can use these; they are not tied to any one app.
"""
from typing import TYPE_CHECKING

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords

if TYPE_CHECKING:
    from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords


class StandardPlatformUpgradeKeywords(BaseKeyword):
    """Standard-lab-correct upgrade/rollback sequence drivers (host order + standby-ready swact guard)."""

    def __init__(self, ssh_connection: SSHConnection):
        """Instance of the class.

        Args:
            ssh_connection(SSHConnection): An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection
        self.swact = SystemHostSwactKeywords(ssh_connection)
        self.alarms = AlarmListKeywords(ssh_connection)

    def upgrade_platform_in_order(self, deploy: "SoftwareDeploySequenceKeywords", version: str, leave_at_activate_done: bool = True) -> None:
        """
        Drive the platform upgrade with a standby-ready wait before each controller swact.

        Used instead of the shared deploy.deploy_upgrade so a standby-readiness wait can be inserted
        before the swact that deploy_host_guarded issues for the active controller - WITHOUT
        modifying the shared swact/deploy keywords. The shared deploy_upgrade loops the hosts and
        calls deploy_host_guarded (which swacts away from an active controller before locking it);
        right after the standby controller was deployed and rebooted it is briefly
        operational=disabled, so that swact is rejected and the run fails. Waiting for the standby to
        be enabled before the swact-sensitive controller step closes that race.

        The sequence mirrors deploy_upgrade exactly, reusing the shared verbs/state waits and the
        guarded per-host step; the only addition is the standby-ready wait before a controller host's
        guarded deploy (a worker deploy issues no swact, so it is not gated).

        Args:
            deploy(SoftwareDeploySequenceKeywords): the shared deploy-sequence keyword whose USM
                verbs, guarded per-host step and state waits are reused.
            version(str): short platform version to upgrade to, e.g. "26.10".
            leave_at_activate_done(bool): leave the deploy at deploy-activate-done for a rollback.

        """
        self.require_no_blocking_alarms()
        deploy.usm.deploy_start(deploy.get_release_id_for_version(version), sudo=False)
        deploy.require_deploy_state("deploy-start-done")
        for host in deploy.usm.deploy_host_upgrade_order():
            if "controller" in host:
                # deploy_host_guarded swacts away from the active controller before locking it;
                # ensure the standby is operationally enabled first so that swact is accepted.
                self.swact.wait_for_standby_available()
            deploy.deploy_host_guarded(host, rollback=False)
        deploy.require_deploy_state("deploy-host-done")
        deploy.usm.software_deploy_activate(sudo=False)
        deploy.require_deploy_state("deploy-activate-done")
        if not leave_at_activate_done:
            deploy.usm.software_deploy_complete(sudo=False)
            deploy.require_deploy_state("deploy-completed")

    def rollback_platform_in_order(self, deploy: "SoftwareDeploySequenceKeywords") -> None:
        """
        Roll the platform back to the from-release, rolling hosts back in the platform's rollback order.

        Kept separate from the shared SoftwareDeploySequenceKeywords.deploy_rollback because that
        shared method rolls the hosts back in the UPGRADE order (standby controller, active
        controller, storage, computes). A rollback requires a different order and the platform
        rejects 'software deploy host-rollback' out of order with "does not satisfy the right order
        of deployment should be <host>", which surfaces only as a non-zero return code and fails the
        run. This is exposed on a standard lab (controller-0/1 + compute-0/1); an AIO-DX lab with no
        workers does not expose it, which is why the shared method has not needed the distinction.

        The platform's rollback host order is:
          - workers (and storage) first, then
          - the controllers in NAME order (controller-0 before controller-1), swacting each
            controller to standby immediately before its own rollback.

        deploy_host_guarded swacts away from the active controller before locking it, so the
        per-controller swact in the documented sequence happens automatically.

        Args:
            deploy(SoftwareDeploySequenceKeywords): the shared deploy-sequence keyword whose USM
                verbs, guarded per-host step and state waits are reused.

        """
        deploy.usm.software_deploy_abort(sudo=False)
        deploy.require_deploy_state("deploy-activate-rollback-pending")
        deploy.usm.software_deploy_activate_rollback(sudo=False)
        deploy.require_deploy_state("deploy-activate-rollback-done")
        for host in self._rollback_host_order(deploy):
            if "controller" in host:
                # deploy_host_guarded swacts away from the active controller before locking it;
                # wait for the standby to be operationally enabled so that swact is accepted.
                self.swact.wait_for_standby_available()
            deploy.deploy_host_guarded(host, rollback=True)
        deploy.require_deploy_state("deploy-host-rollback-done")
        deploy.usm.software_deploy_delete(sudo=False)

    def _rollback_host_order(self, deploy: "SoftwareDeploySequenceKeywords") -> list:
        """
        Build the platform's rollback host order: workers, storage, then controllers by name.

        The controller order is by NAME, not by role. The platform enforces controller-0 before
        controller-1 and rejects an out-of-order controller rollback with "does not satisfy the
        right order of deployment should be controller-0". A role-derived order is wrong because the
        active/standby roles swap during the upgrade, so sorting the controllers by name is stable
        across the swaps and matches what the platform demands.

        The per-controller swact in the documented sequence is handled by deploy_host_guarded.

        Args:
            deploy(SoftwareDeploySequenceKeywords): provides the USM role/host-list helpers.

        Returns:
            list[str]: ordered hostnames: workers (sorted by name), storage (sorted by name),
                controllers (sorted by name).
        """
        computes = sorted(host.get_host_name() for host in deploy.usm.computes_host_upgrade_list())
        storages = sorted(host.get_host_name() for host in deploy.usm.storage_host_upgrade_list())
        active = deploy.usm.active_controller_host_upgrade()
        standby = deploy.usm.standby_controller_host_upgrade()
        controller_names = [active.get_host_name()]
        if standby is not None:
            controller_names.append(standby.get_host_name())
        controllers = sorted(controller_names)

        order: list = []
        order.extend(computes)
        order.extend(storages)
        order.extend(controllers)
        get_logger().log_info(f"rollback host order (controllers by name): {order}")
        return order

    def require_no_blocking_alarms(self) -> None:
        """
        Fail, naming the offending alarms, when an active alarm would block 'deploy start'.

        'software deploy start' runs its own health check and refuses on any active alarm, returning
        only a non-zero code with "No alarms: [Fail]" and a count - so a bare failure makes the
        caller go read the deploy log to find what was wrong. Reading the alarms here first turns
        that into a message that names them (reusing the shared public AlarmListKeywords).

        Raises:
            KeywordException: when any alarm is active.

        """
        alarms = self.alarms.alarm_list()
        if alarms:
            described = ", ".join(f"{alarm.get_alarm_id()} ({alarm.get_entity_id()})" for alarm in alarms)
            raise KeywordException(
                f"Refusing to start a deploy with {len(alarms)} active alarm(s): {described}. "
                f"'software deploy start' rejects any alarm, so this would fail with only a count "
                f"reported. Clear the alarms, or if they are test artifacts, remove whatever raised "
                f"them before upgrading."
            )
