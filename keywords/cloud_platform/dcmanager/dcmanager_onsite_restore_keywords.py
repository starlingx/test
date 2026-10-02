"""Keywords orchestrating onsite restore without reinstall.

Composes the seed build, HTTPS staging, RVMC mount, restore monitoring, and health
validation into a single flow. Monitoring is done in two phases: a fail-fast
"started" phase (validate_not_equals_with_retry on deploy_status, which must leave
'factory-restore-complete' after the seed mount) and a "completion" phase (the
shared DcManagerSubcloudStateWatcherKeywords.watch_single_subcloud, until
deploy_status reaches 'complete'), the same watcher the existing DC restore/backup
flows use.
"""

from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry, validate_not_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_state_watcher_keywords import (
    ONSITE_RESTORE_COMPLETE_STATE,
    ONSITE_RESTORE_FAILED_STATES,
    ONSITE_RESTORE_IN_PROGRESS_STATES,
    ONSITE_RESTORE_START_STATE,
    DcManagerSubcloudStateWatcherKeywords,
)
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.nocloud.seed_iso_builder_keywords import SeedIsoBuilderKeywords
from keywords.cloud_platform.nocloud.seed_iso_staging_keywords import SeedIsoStagingKeywords
from keywords.cloud_platform.rvmc.rvmc_mount_keywords import RvmcMountKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords

# Phase A (started) timeout: time allowed, after mounting the seed ISO, for the
# subcloud to leave the 'factory-restore-complete' start state. This proves the
# seed mount triggered cloud-init and the SC accepted the restore request; if it
# never leaves within this window the mount/trigger failed and we fail fast rather
# than wait out the full completion timeout.
START_TIMEOUT = 900
# Phase B (completion) timeout: the full restore playbook, unlock, post-unlock
# reboot and restore-complete.
DEFAULT_MONITOR_TIMEOUT = 5400
MONITOR_POLL_INTERVAL = 60
# After deploy_status reaches 'complete', the subcloud still performs a post-unlock
# reboot + restore-complete before availability returns to 'online' (~9-10 min per
# KPI). The shared availability validator only waits 300s, so this flow waits with a
# restore-appropriate timeout before checking health.
POST_RESTORE_ONLINE_TIMEOUT = 1200
POST_RESTORE_ONLINE_POLL_INTERVAL = 10
SUBCLOUD_AVAILABILITY_ONLINE = "online"
# After the subcloud comes online, platform applications re-apply (restore-complete
# re-apply, per KPI P5) and are transiently in 'applying' before settling. Wait for
# all apps to reach a stable status before the strict single-shot health check so it
# does not race the app re-apply.
POST_RESTORE_APP_STABLE_STATES = ["applied", "uploaded"]
POST_RESTORE_APP_SETTLE_TIMEOUT = 1800
POST_RESTORE_APP_SETTLE_POLL_INTERVAL = 30


class DcManagerOnsiteRestoreKeywords(BaseKeyword):
    """Keywords orchestrating the onsite restore without reinstall flow."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize DcManagerOnsiteRestoreKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active System Controller.
        """
        self.ssh_connection = ssh_connection

    def onsite_restore_without_reinstall(self, subcloud_name: str, local_only: bool, restore_timeout: Optional[int] = None) -> None:
        """Run the full onsite restore without reinstall flow for a subcloud.

        Builds the onsite-restore seed ISO, stages it on the SC HTTPS tree, mounts
        it on the subcloud via RVMC (set_boot_override and poweroff_host excluded),
        then monitors the restore to completion and validates availability and
        cluster health.

        Args:
            subcloud_name (str): Name of the target subcloud.
            local_only (bool): True to restore from the subcloud's local backup;
                False to have the System Controller transfer the central backup.
            restore_timeout (Optional[int]): deploy_status monitoring timeout in seconds.
                When None, DEFAULT_MONITOR_TIMEOUT is used.
        """
        software_version = DcManagerSubcloudShowKeywords(self.ssh_connection).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

        get_logger().log_test_case_step(f"Building onsite-restore seed ISO for {subcloud_name} (local_only={local_only})")
        seed_iso_path = SeedIsoBuilderKeywords(self.ssh_connection).build_onsite_restore_seed(subcloud_name, local_only, restore_timeout)

        get_logger().log_test_case_step(f"Staging seed ISO to the SC HTTPS tree for {subcloud_name}")
        staged_path = SeedIsoStagingKeywords(self.ssh_connection).stage_seed_iso_to_https(subcloud_name, seed_iso_path, software_version)

        get_logger().log_test_case_step(f"Mounting seed ISO on {subcloud_name} via RVMC (without reinstall)")
        RvmcMountKeywords(self.ssh_connection).mount_seed_iso(subcloud_name, staged_path)

        self._monitor_restore(subcloud_name, restore_timeout)
        self._validate_post_restore(subcloud_name)

    def _monitor_restore(self, subcloud_name: str, restore_timeout: Optional[int] = None) -> None:
        """Monitor the on-site restore in two phases via dcmanager deploy_status.

        Phase A (started): confirm the subcloud LEAVES the 'factory-restore-complete'
        start state within START_TIMEOUT. This proves the seed mount triggered
        cloud-init and the SC accepted the restore request; if it never leaves, the
        mount/trigger failed and we fail fast rather than wait out the full
        completion timeout. Uses the shared state watcher's fail-fast "leaves"
        variant.

        Phase B (complete): wait until deploy_status reaches 'complete', failing on
        'restore-failed'/'restore-prep-failed', using the shared state watcher
        (the same mechanism the existing DC restore/backup flows use). The onsite
        in-progress set includes the start state so the pre-trigger window is not
        treated as an unexpected state.

        Args:
            subcloud_name (str): Name of the target subcloud.
            restore_timeout (Optional[int]): Phase B monitoring timeout in seconds.
                When None, DEFAULT_MONITOR_TIMEOUT is used.
        """
        complete_timeout = restore_timeout if restore_timeout is not None else DEFAULT_MONITOR_TIMEOUT
        watcher = DcManagerSubcloudStateWatcherKeywords(self.ssh_connection)

        # Phase A: confirm the restore actually started (seed mount + trigger worked)
        # by waiting for deploy_status to leave the factory-restore-complete start
        # state, failing fast if it never does. Uses the shared
        # validate_not_equals_with_retry; a terminal failure state is raised from
        # inside the polled callable.
        get_logger().log_test_case_step(f"Confirming onsite restore started for {subcloud_name} (deploy_status leaves '{ONSITE_RESTORE_START_STATE}')")

        def get_deploy_status() -> str:
            """Return the subcloud deploy_status, raising on a terminal failure state.

            Returns:
                str: The current deploy_status reported by dcmanager.

            Raises:
                Exception: If deploy_status is a terminal onsite-restore failure state.
            """
            deploy_status = DcManagerSubcloudShowKeywords(self.ssh_connection).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_deploy_status()
            if deploy_status in ONSITE_RESTORE_FAILED_STATES:
                raise Exception(f"Subcloud {subcloud_name} onsite restore failed to start; deploy_status='{deploy_status}'")
            return deploy_status

        validate_not_equals_with_retry(
            function_to_execute=get_deploy_status,
            not_expected_value=ONSITE_RESTORE_START_STATE,
            validation_description=f"Subcloud {subcloud_name} deploy_status leaves '{ONSITE_RESTORE_START_STATE}' (onsite restore started).",
            timeout=START_TIMEOUT,
            polling_sleep_time=MONITOR_POLL_INTERVAL,
        )

        # Phase B: wait for the restore to reach 'complete'.
        get_logger().log_test_case_step(f"Monitoring onsite restore for {subcloud_name} (deploy_status -> '{ONSITE_RESTORE_COMPLETE_STATE}')")
        watcher.watch_single_subcloud(
            subcloud_name=subcloud_name,
            field_to_watch="deploy_status",
            in_progress_states=ONSITE_RESTORE_IN_PROGRESS_STATES,
            complete_state=ONSITE_RESTORE_COMPLETE_STATE,
            failed_states=ONSITE_RESTORE_FAILED_STATES,
            timeout=complete_timeout,
            polling_interval=MONITOR_POLL_INTERVAL,
        )

    def _validate_post_restore(self, subcloud_name: str) -> None:
        """Validate the subcloud is online and the cluster is healthy after restore.

        Follows the existing DC restore/enroll assertion pattern: validate
        availability online, then validate cluster health (alarms, pods, apps).
        After deploy_status 'complete' the subcloud still does a post-unlock reboot
        before availability returns to 'online', so this waits with a
        restore-appropriate timeout (POST_RESTORE_ONLINE_TIMEOUT) rather than the
        shared availability validator's shorter default.

        Args:
            subcloud_name (str): Name of the target subcloud.
        """
        get_logger().log_test_case_step(f"Validating {subcloud_name} is online after restore")

        def get_availability() -> str:
            return DcManagerSubcloudListKeywords(self.ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name).get_availability()

        validate_equals_with_retry(
            function_to_execute=get_availability,
            expected_value=SUBCLOUD_AVAILABILITY_ONLINE,
            validation_description=f"Subcloud {subcloud_name} availability reaches '{SUBCLOUD_AVAILABILITY_ONLINE}' after restore.",
            timeout=POST_RESTORE_ONLINE_TIMEOUT,
            polling_sleep_time=POST_RESTORE_ONLINE_POLL_INTERVAL,
        )

        get_logger().log_test_case_step(f"Waiting for {subcloud_name} applications to settle after restore")
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        SystemApplicationListKeywords(subcloud_ssh).validate_all_apps_status(
            POST_RESTORE_APP_STABLE_STATES,
            timeout=POST_RESTORE_APP_SETTLE_TIMEOUT,
            polling_sleep_time=POST_RESTORE_APP_SETTLE_POLL_INTERVAL,
        )

        get_logger().log_test_case_step(f"Validating cluster health on {subcloud_name} after restore")
        HealthKeywords(subcloud_ssh).validate_healty_cluster()
