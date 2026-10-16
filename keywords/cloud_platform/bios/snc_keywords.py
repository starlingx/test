"""Keyword for the sub-NUMA clustering (SNC/NPS) BIOS test cases.

The enable and disable SNC test cases both drive a NUMA-related BIOS
attribute to a target value, reboot the host to apply it, bring the
controller back online, and verify the BMC reports the target value. The
only differences between the tests are the target intent (enable/disable)
and whether the original value is restored afterward, so the shared
machinery lives in :class:`SncKeywords`.

The attribute name and its values differ per BMC vendor (HPE
``SubNumaClustering``, Dell ``SubNumaCluster``, AMD/Supermicro
``NUMANodesPerSocket``), so the test cases pass vendor-neutral intent
markers (:data:`SncKeywords.SNC_ENABLED` / :data:`SncKeywords.SNC_DISABLED`)
and this keyword resolves them to the correct per-vendor value at runtime
via :meth:`SncKeywords.resolve_snc_profile`.
"""

import time

import pytest

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_none
from keywords.base_keyword import BaseKeyword
from keywords.bmc.biostool.biostool_keywords import BiosToolKeywords
from keywords.bmc.biostool.objects.numa_attribute_report import NumaAttributeReport
from keywords.cloud_platform.bios.objects.snc_profile import SncProfile
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.postgresql.object.icpu_numa_cpu_output import IcpuNumaCpuOutput
from keywords.cloud_platform.postgresql.postgresql_keywords import PostgresqlKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.lscpu.lscpu_keywords import LscpuKeywords
from keywords.linux.sysfs.sysfs_numa_keywords import SysfsNumaKeywords


class SncKeywords(BaseKeyword):
    """Vendor-adaptive sub-NUMA clustering (SNC/NPS) orchestration.

    Drives a NUMA-related BIOS attribute to an enabled/disabled target over
    Redfish (vendor-adaptive via :data:`SncKeywords._SNC_PROFILES`), reboots
    the host through the BMC to apply it, brings the controller back online,
    and verifies the result.

    This keyword needs both an SSH connection to the StarlingX host (to
    lock/unlock, read alarms, and read the realized NUMA topology) and the
    BMC credentials (to stage/apply the BIOS change over Redfish). The BMC
    keyword is built from lab config on demand.
    """

    # Intent markers passed by the test wrappers. These are NOT raw BIOS
    # values; they are resolved to the vendor-specific attribute value at
    # runtime (see resolve_snc_profile), because the attribute name and its
    # "on"/"off" values differ per BMC vendor:
    #
    #   Vendor       Attribute             Enable value     Disable value
    #   -----------  --------------------  ---------------  -------------
    #   HPE (iLO)    SubNumaClustering     Enabled          Disabled
    #   Dell (iDRAC) SubNumaCluster        4-Way (or 2-Way) Disabled
    #   AMD/SMC      NUMANodesPerSocket    NPS2 (or NPS4)   NPS1
    #
    # For AMD/NPS there is no literal "Disabled"; sub-NUMA OFF == NPS1 (one
    # node per socket). The BIOS keyword accepts either the ValueName or
    # ValueDisplayName and translates to the form the BMC expects.
    SNC_ENABLED = "__SNC_ENABLE__"
    SNC_DISABLED = "__SNC_DISABLE__"

    # Per-vendor SNC profiles, matched (case-insensitive) by substring
    # against the BMC-reported Manufacturer.
    # Each profile's enable value is an ordered candidate list: the first
    # candidate the BMC lists as allowable is used, so a profile adapts to a
    # platform that supports a higher clustering level while falling back on
    # ones that do not.
    _SNC_PROFILES = [
        SncProfile(manufacturer="hpe", attribute="SubNumaClustering", enable_candidates=["Enabled"], disable="Disabled"),
        # Dell: prefer 4-Way where the platform supports it, else 2-Way. Both
        # realize sub-NUMA clustering; some Dell boxes offer only 2-Way.
        SncProfile(manufacturer="dell", attribute="SubNumaCluster", enable_candidates=["4-Way", "2-Way"], disable="Disabled"),
        # Supermicro (and other AMD/NPS platforms): "enable" targets NPS2
        # (two NUMA nodes per socket). "disable" is NPS1 (one NUMA node per
        # socket), as there is no literal Disabled value for
        # NUMANodesPerSocket.
        SncProfile(manufacturer="supermicro", attribute="NUMANodesPerSocket", enable_candidates=["NPS2"], disable="NPS1"),
    ]

    # Seconds to wait after the BMC reset before the host is SSH-reachable
    # again. A BIOS attribute change forces a longer POST (memory retraining
    # on NUMA/SNC changes in particular), so this is generous on real
    # hardware.
    SSH_BACK_WAIT_SECONDS = 1800
    POST_RESET_POLL_INTERVAL_SECONDS = 30

    # Seconds to wait, after SSH is back, for the StarlingX control plane
    # (fm/sysinv) to answer before unlock_host's pre-checks will pass.
    PLATFORM_READY_WAIT_SECONDS = 1800

    # Seconds for unlock_host's "accepted" polling window. On a simplex the
    # unlock triggers a reboot during which SSH is unreachable for minutes;
    # the default 300s can expire inside that outage and raise a spurious
    # unlock timeout, so we widen it to ride through the post-unlock reboot.
    UNLOCK_ACCEPTED_TIMEOUT_SECONDS = 1800

    # Alarms that are standing/environmental on some labs and unrelated to the
    # BIOS/SNC change under test, so the post-reboot settle wait must tolerate
    # them rather than block forever waiting for a fully clear alarm list:
    #   100.119 - "not locked to remote PTP Grand Master" (labs with a PTP
    #             instance configured but no real Grand Master to lock to).
    SETTLE_WAIT_EXCLUDED_ALARM_IDS = ["100.119"]

    # sysinv agent source file whose NUMA discovery must read the OS sysfs
    # topology (/sys/devices/system/node) rather than the old physical_id
    # from /proc/cpuinfo.
    SYSINV_NODE_AGENT_PATH = "/usr/lib/python3/dist-packages/sysinv/agent/node.py"
    SYSFS_NODE_TOKEN = "sys/devices/system/node"

    def __init__(self, host_name: str = "controller-0"):
        """Initialize an SncKeywords.

        Args:
            host_name (str): The StarlingX host to operate on (the host
                whose BIOS is changed and whose NUMA topology is checked).
        """
        self.host_name = host_name

    # --- public orchestration ---

    def set_snc(self, request: pytest.FixtureRequest, target_value: str, restore: bool = True) -> None:
        """Drive the BIOS SNC attribute to a target and verify it (vendor-aware).

        Detects the BMC vendor, maps ``target_value`` (an intent marker like
        SNC_ENABLED/SNC_DISABLED, or an explicit literal) to the
        vendor-specific BIOS attribute and value, reboots the host to apply
        the change, brings the controller back online, and verifies the BMC
        reports the resolved value. The BMC attribute value is the source of
        truth; the OS online-node count is logged for information only,
        because it does not change with SNC alone on all hardware (e.g. HPE
        ProLiant Gen10).

        WARNING: DISRUPTIVE. Stages a BIOS change and reboots the host.

        Args:
            request (pytest.FixtureRequest): The pytest request, used to
                register the teardown.
            target_value (str): SNC_ENABLED / SNC_DISABLED intent marker, or
                an explicit literal BIOS value (e.g. "NPS4").
            restore (bool): When True (default, the regression-test
                behavior), teardown puts the BIOS attribute back to the
                value observed before the test, so the change does not
                persist. When False, the change persists: teardown only
                ensures the controller is left unlocked.
        """
        bios_tool = self._get_bios_tool()
        ssh_connection = self._get_ssh()

        # Precondition: the controller must start unlocked. If a previous run
        # or a defect left it locked, fail loudly rather than silently
        # recovering. Teardown will still attempt to leave the lab unlocked.
        start_admin_state = self._get_admin_state(ssh_connection)
        validate_equals(start_admin_state, "unlocked", f"{self.host_name} is unlocked at test start")

        # Resolve the vendor profile and the concrete target value.
        profile = self.resolve_snc_profile(bios_tool)
        snc_attribute = profile.get_attribute()

        # Discover the current attribute first: its BMC-allowable values drive
        # which enable candidate is selected, and its current value is the
        # starting point teardown restores.
        start_attrs = self._discover(bios_tool)
        resolved_target = self._resolve_target_value(profile, target_value, start_attrs[snc_attribute])
        original_value = start_attrs[snc_attribute].get_current_value()
        get_logger().log_info(f"Starting BIOS '{snc_attribute}' value is '{original_value}'; target is '{resolved_target}'")

        baseline_node_count = SysfsNumaKeywords(ssh_connection).get_online_nodes().get_online_node_count()
        get_logger().log_info(f"Baseline: {baseline_node_count} online NUMA node(s)")

        def teardown() -> None:
            """Leave the controller unlocked; optionally restore the SNC value."""
            if restore:
                get_logger().log_teardown_step("Restore BIOS SNC value and leave the controller unlocked")
                try:
                    current = self._discover(bios_tool).get(snc_attribute)
                    if current is not None and current.get_current_value() != original_value:
                        get_logger().log_info(f"Restoring '{snc_attribute}' from '{current.get_current_value()}' back to '{original_value}'")
                        self._apply_and_reboot(bios_tool, {snc_attribute: original_value})
                except Exception as ex:  # noqa: BLE001 - teardown must not mask the test result
                    get_logger().log_info(f"Teardown could not restore the BIOS value: {ex}")
                finally:
                    self.ensure_controller_unlocked()
            else:
                get_logger().log_teardown_step(f"Leave BIOS '{snc_attribute}' at the new value and ensure the controller is unlocked")
                self.ensure_controller_unlocked()

        request.addfinalizer(teardown)

        if original_value == resolved_target:
            get_logger().log_info(f"'{snc_attribute}' is already '{resolved_target}'; nothing to change.")
        else:
            get_logger().log_test_case_step(f"Drive BIOS '{snc_attribute}' to '{resolved_target}' and reboot to apply")
            self._apply_and_reboot(bios_tool, {snc_attribute: resolved_target})

            get_logger().log_test_case_step(f"Unlock {self.host_name} after the reboot")
            new_ssh = self._get_ssh()
            # On a simplex the unlock itself triggers a reboot, during which
            # SSH is unreachable for several minutes. unlock_host's default
            # "accepted" polling window (300s) can expire inside that SSH
            # outage and raise a spurious "Timeout: failed to unlock" even
            # though the unlock was accepted. Give the accepted phase enough
            # room to ride through the post-unlock reboot before
            # wait_for_host_unlocked takes over.
            unlock_success = SystemHostLockKeywords(new_ssh).unlock_host(self.host_name, unlock_accepted_timeout=self.UNLOCK_ACCEPTED_TIMEOUT_SECONDS)
            validate_equals(unlock_success, True, f"{self.host_name} unlocked after BIOS change")

        get_logger().log_test_case_step(f"Verify the BMC reports '{snc_attribute}' = '{resolved_target}'")
        after = self._discover(bios_tool)
        validate_equals(after[snc_attribute].get_current_value(), resolved_target, f"BMC reports '{snc_attribute}' is '{resolved_target}' after the change")

        # Informational only: OS online-node count may not change with SNC alone.
        final_ssh = self._get_ssh()
        final_node_count = SysfsNumaKeywords(final_ssh).get_online_nodes().get_online_node_count()
        get_logger().log_info(f"After setting '{snc_attribute}' to '{resolved_target}': {final_node_count} online NUMA node(s) (baseline was {baseline_node_count})")

    def verify_numa_topology(self, request: pytest.FixtureRequest) -> None:
        """Enable sub-NUMA clustering and verify the NUMA topology propagated.

        Enables SNC/NPS (vendor-adaptive, via :meth:`set_snc`), rebooting the
        host once, then verifies the resulting NUMA topology is detected
        consistently across layers. The expected total NUMA node count is
        ``sockets x nodes_per_socket`` (so a dual-socket system with 2 nodes
        per socket is expected to show 4 NUMA nodes total).

        All checks are evaluated (none short-circuits the others) and each is
        logged with an explicit PASS/FAIL line, so a failing run makes clear
        exactly which layer disagreed. The method then fails if any check
        failed.

        Checks performed after SNC is enabled:
          - OS: ``/sys/devices/system/node/online`` node count == expected
          - sysinv CLI: ``system host-cpu-list`` processor count == expected
            (the ``processor`` column is the sysinv NUMA node, so this
            reflects the ``i_icpu`` NUMA-node count via a supported API)

        WARNING: DISRUPTIVE. Enables SNC and reboots the host. A teardown
        restores the original BIOS value and leaves the controller unlocked.

        Args:
            request (pytest.FixtureRequest): The pytest request, used to
                register the restore/unlock teardown.
        """
        # Enable SNC/NPS (vendor-adaptive) with the shared set-and-restore
        # machinery. This performs the single lock -> stage -> reset -> unlock
        # cycle and registers teardown to restore the original value.
        self.set_snc(request, self.SNC_ENABLED)

        # unlock_host returns once the host reports available/unlocked/enabled
        # with no config-out-of-date alarm, but on a simplex the unlock
        # triggers a second reboot and the platform then passes through
        # Multi-Node Recovery Mode (alarm 700.016) with services still coming
        # up. Querying sysinv (host-cpu-list) in that window fails
        # intermittently, so wait for the platform to fully settle before
        # running the topology checks.
        self._wait_for_platform_fully_settled()

        ssh_connection = self._get_ssh()

        lscpu = LscpuKeywords(ssh_connection).get_lscpu()
        socket_count = lscpu.get_socket_count()
        os_node_count = SysfsNumaKeywords(ssh_connection).get_online_nodes().get_online_node_count()
        nodes_per_socket = max(os_node_count // socket_count, 1) if socket_count > 0 else max(os_node_count, 1)
        expected_total_nodes = socket_count * nodes_per_socket
        get_logger().log_info(f"Sockets={socket_count}, nodes/socket={nodes_per_socket} -> expected total NUMA nodes = {expected_total_nodes}")

        # Evaluate every check, collecting (passed, observed) without raising,
        # so one failing layer does not hide the others. The dict preserves
        # insertion order so the summary reads in a stable order.
        results: dict[str, tuple[bool, object]] = {}

        results["OS /sys node count"] = (os_node_count == expected_total_nodes, os_node_count)

        cli_node_count = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(self.host_name).get_processor_count()
        results["sysinv host-cpu-list processor count"] = (cli_node_count == expected_total_nodes, cli_node_count)

        failed_checks = []
        for check_name, (passed, observed) in results.items():
            status = "PASS" if passed else "FAIL"
            get_logger().log_info(f"NUMA topology check [{status}]: {check_name} = {observed} (expected {expected_total_nodes})")
            if not passed:
                failed_checks.append(f"{check_name} (got {observed}, expected {expected_total_nodes})")

        validate_equals(failed_checks, [], "All NUMA topology checks match the expected node count")

    def verify_numa_cpu_mapping(self, request: pytest.FixtureRequest) -> None:
        """Verify sysinv derives NUMA CPU mapping from sysfs, matching the OS.

        Confirms that sysinv discovers NUMA nodes from
        ``/sys/devices/system/node`` (not the old ``physical_id`` from
        ``/proc/cpuinfo``) and that the sysinv DB's CPU-to-NUMA-node mapping
        matches the OS sysfs topology.

        SNC is enabled first (vendor-adaptive, via :meth:`set_snc`) so there
        is more than one NUMA node per socket to distinguish the sysfs path
        from the old socket assumption, then three checks run:
          1. the sysinv agent source references ``/sys/devices/system/node``;
          2. the sysinv DB (``i_icpu`` grouped by ``forinodeid``) reports the
             expected per-node CPU sets; and
          3. those DB per-node CPU sets match the OS
             ``/sys/devices/system/node/node*/cpulist``.

        All checks are evaluated (none short-circuits the others) and each is
        logged with an explicit PASS/FAIL line; the method fails if any
        check failed.

        WARNING: DISRUPTIVE. Enables SNC and reboots the host. A teardown
        restores the original BIOS value and leaves the controller unlocked.

        Args:
            request (pytest.FixtureRequest): The pytest request, used to
                register the restore/unlock teardown.
        """
        # Precondition: SNC enabled (vendor-adaptive) with the shared machinery,
        # then wait for the platform to fully settle after the unlock reboot.
        self.set_snc(request, self.SNC_ENABLED)
        self._wait_for_platform_fully_settled()

        ssh_connection = self._get_ssh()

        # Collect (passed, observed) for every check without raising, so one
        # failing layer does not hide the others.
        results: dict[str, tuple[bool, object]] = {}

        # Check 1: the sysinv agent reads NUMA topology from the OS sysfs path.
        code_match = FileKeywords(ssh_connection).grep_file_with_sudo(self.SYSINV_NODE_AGENT_PATH, self.SYSFS_NODE_TOKEN).strip()
        results[f"sysinv agent references '{self.SYSFS_NODE_TOKEN}'"] = (code_match != "", code_match[:80] if code_match else "<no match>")

        # Checks 2 & 3: the DB per-node CPU sets exist and match the OS sysfs.
        db_node_cpus = self._get_db_node_cpu_sets(ssh_connection)
        os_node_cpus = SysfsNumaKeywords(ssh_connection).get_node_cpu_sets()

        results["sysinv DB reports >1 NUMA node (SNC enabled)"] = (len(db_node_cpus) > 1, len(db_node_cpus))
        results["sysinv DB per-node CPU sets match OS sysfs cpulist"] = (db_node_cpus == os_node_cpus, f"DB={db_node_cpus} OS={os_node_cpus}")

        failed_checks = []
        for check_name, (passed, observed) in results.items():
            status = "PASS" if passed else "FAIL"
            get_logger().log_info(f"NUMA CPU mapping check [{status}]: {check_name} -> {observed}")
            if not passed:
                failed_checks.append(f"{check_name} (observed {observed})")

        validate_equals(failed_checks, [], "sysinv NUMA CPU mapping is derived from sysfs and matches the OS")

    def ensure_controller_unlocked(self) -> None:
        """Leave the host unlocked, recovering it if it is currently locked.

        No-op if the host is already unlocked. Used by teardown to leave the
        lab in a good state for the next test, and as the entry point for a
        recovery test that frees a lab left locked by an interrupted run.
        """
        ssh_connection = self._get_ssh()
        admin_state = self._get_admin_state(ssh_connection)
        get_logger().log_info(f"{self.host_name} administrative state is '{admin_state}'")
        if admin_state == "unlocked":
            return

        self._wait_for_platform_services(ssh_connection)
        unlock_success = SystemHostLockKeywords(ssh_connection).unlock_host(self.host_name, unlock_accepted_timeout=self.UNLOCK_ACCEPTED_TIMEOUT_SECONDS)
        validate_equals(unlock_success, True, f"{self.host_name} unlocked to restore the lab state")

    def resolve_snc_profile(self, bios_tool: BiosToolKeywords) -> SncProfile:
        """Resolve the SNC profile for the BMC under test.

        Reads the BMC Manufacturer via the ``sysinfo`` keyword and selects
        the matching per-vendor profile from :data:`_SNC_PROFILES`, then
        confirms the profile's attribute is actually present among the
        discovered NUMA attributes. This lets a single set of SNC test cases
        run across HPE, Dell, and AMD/Supermicro without hardcoding one
        vendor's names.

        Args:
            bios_tool (BiosToolKeywords): The BMC keyword to query.

        Returns:
            SncProfile: The matched vendor profile.

        Raises:
            AssertionError: via validate_* if no profile matches the
                Manufacturer or the profile's attribute is not present.
        """
        system_info = bios_tool.sysinfo()
        manufacturer = (system_info.get_manufacturer() or "").lower()
        get_logger().log_info(f"BMC Manufacturer reported as '{system_info.get_manufacturer()}'")

        profile = next((p for p in self._SNC_PROFILES if p.get_manufacturer() in manufacturer), None)
        validate_not_none(profile, f"A known SNC profile exists for Manufacturer '{system_info.get_manufacturer()}'")

        discovered = self._discover(bios_tool)
        validate_equals(profile.get_attribute() in discovered, True, f"profile attribute '{profile.get_attribute()}' is present on this BMC (discovered: {list(discovered)})")
        return profile

    # --- internal helpers ---

    def _resolve_target_value(self, profile: SncProfile, target_value: str, attribute_report: NumaAttributeReport) -> str:
        """Translate an intent marker (or literal value) to a BIOS value.

        For the ``SNC_ENABLED`` intent, picks the first of the profile's
        enable candidates that this specific BMC lists as allowable (so a
        4-Way-capable Dell gets 4-Way while a 2-Way-only Dell gets 2-Way).
        If the BMC does not publish allowable values, the most-preferred
        candidate is used.

        Args:
            profile (SncProfile): The vendor SNC profile.
            target_value (str): Either an intent marker (SNC_ENABLED /
                SNC_DISABLED) or an explicit literal BIOS value.
            attribute_report (NumaAttributeReport): The discovered report for
                the profile's attribute, used to read the BMC's allowable
                values.

        Returns:
            str: The concrete BIOS attribute value to set.

        Raises:
            AssertionError: via validate_* if none of the enable candidates
                is allowable on this BMC.
        """
        if target_value == self.SNC_DISABLED:
            return profile.get_disable_value()
        if target_value != self.SNC_ENABLED:
            return target_value  # caller passed an explicit literal value

        allowable = attribute_report.get_allowable_values()
        chosen = profile.select_enable_value(allowable)
        validate_not_none(chosen, f"an enable candidate {profile.get_enable_candidates()} for '{profile.get_attribute()}' is allowable on this BMC (allowable: {allowable})")
        return chosen

    def _apply_and_reboot(self, bios_tool: BiosToolKeywords, attributes: dict[str, str]) -> None:
        """Lock the controller, stage BIOS attributes, reset via BMC, and wait.

        Locks the host, stages the given BIOS attributes over Redfish, resets
        the host through the BMC to apply them, then waits until the OS is
        SSH-reachable again and the StarlingX control plane answers. The
        caller is responsible for unlocking afterward.

        Args:
            bios_tool (BiosToolKeywords): The BMC keyword to stage/reset with.
            attributes (dict[str, str]): BIOS attribute name -> value to stage.
        """
        ssh_connection = self._get_ssh()
        if self._get_admin_state(ssh_connection) != "locked":
            get_logger().log_info(f"Locking {self.host_name} before the BIOS change")
            lock_success = SystemHostLockKeywords(ssh_connection).lock_host(self.host_name)
            validate_equals(lock_success, True, f"{self.host_name} locked before BIOS change")

        get_logger().log_info(f"Staging BIOS attributes {attributes} over Redfish")
        bios_tool.set_numa_attributes(attributes)

        get_logger().log_info("Resetting the host via the BMC to apply the staged BIOS change")
        bios_tool.reset_host()

        get_logger().log_info(f"Waiting up to {self.SSH_BACK_WAIT_SECONDS}s for the host to be SSH-reachable after reset")
        self._wait_for_ssh_back()

        get_logger().log_info(f"Waiting for {self.host_name} control plane to answer before proceeding")
        new_ssh = self._get_ssh()
        self._wait_for_platform_services(new_ssh)

    def _wait_for_platform_fully_settled(self) -> None:
        """Wait for the controller to be fully recovered after the unlock reboot.

        On a simplex the ``unlock_host`` performed by :meth:`set_snc`
        triggers a second reboot, after which the platform passes through
        Multi-Node Recovery Mode (alarm 700.016) with service groups still
        coming up. ``unlock_host`` returns once the host is
        available/unlocked/enabled with no config-out-of-date alarm, which
        can be before the control plane is fully serving -- so sysinv queries
        (``host-cpu-list``) run in that window fail intermittently.

        This waits for two conditions before the topology checks run:
          1. the host reports availability == "available", and
          2. all alarms clear and stay clear for a short dwell, tolerating
             the transient query failures that occur while platform services
             are still restarting.

        Raises:
            TimeoutError: If the host does not become available, or the
                alarms do not clear and stay clear, within the keyword
                timeouts.
        """
        ssh_connection = self._get_ssh()
        get_logger().log_info("Waiting for the controller to report availability 'available' after the unlock reboot")
        SystemHostListKeywords(ssh_connection).wait_for_host_availability(self.host_name, ["available"])

        get_logger().log_info("Waiting for all alarms (incl. Multi-Node Recovery Mode) to clear and stay clear before running topology checks")
        # Use the _excluding variant so that:
        #  - query failures are tolerated: while platform services restart,
        #    'fm alarm-list' itself fails (connection refused / keystone
        #    unavailable), which must be treated as "not ready yet" rather
        #    than aborting the wait; and
        #  - standing environmental alarms unrelated to the SNC change (e.g.
        #    100.119 PTP no-lock on some labs) are excluded, so the wait does
        #    not block forever on an alarm that never clears.
        AlarmListKeywords(ssh_connection).wait_for_all_alarms_cleared_excluding(
            excluded_alarm_ids=self.SETTLE_WAIT_EXCLUDED_ALARM_IDS,
            tolerate_query_failure=True,
            dwell_seconds=60,
        )

    def _get_bios_tool(self) -> BiosToolKeywords:
        """Build a BiosToolKeywords for this host's BMC from lab config.

        Returns:
            BiosToolKeywords: The BMC keyword for this host.

        Raises:
            AssertionError: via validate_* if the host or its bm_ip is not
                configured in the lab config.
        """
        node = ConfigurationManager.get_lab_config().get_node(self.host_name)
        validate_not_none(node, f"{self.host_name} exists in the lab config")
        validate_not_none(node.get_bm_ip(), f"{self.host_name} has a bm_ip configured")
        return BiosToolKeywords(node.get_bm_ip(), node.get_bm_username(), node.get_bm_password())

    def _get_ssh(self) -> SSHConnection:
        """Return a fresh SSH connection to this host.

        Returns:
            SSHConnection: An SSH connection to this host.
        """
        return LabConnectionKeywords().get_ssh_for_hostname(self.host_name)

    def _discover(self, bios_tool: BiosToolKeywords) -> dict[str, NumaAttributeReport]:
        """Return discovered NUMA attributes keyed by attribute name.

        Args:
            bios_tool (BiosToolKeywords): The BMC keyword to query.

        Returns:
            dict[str, NumaAttributeReport]: Mapping of attribute name to its
            report object.
        """
        return {report.get_attribute(): report for report in bios_tool.discover_numa_attributes()}

    def _get_admin_state(self, ssh_connection: SSHConnection) -> str:
        """Return the controller's administrative state ('locked'/'unlocked').

        Waits for the StarlingX control plane to answer first, so this is
        safe to call shortly after a reboot/unlock when ``system host-list``
        would otherwise fail with "credentials can only be loaded from the
        active controller" (return code 1).

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.

        Returns:
            str: The administrative state.
        """
        self._wait_for_platform_services(ssh_connection)
        host = SystemHostListKeywords(ssh_connection).get_system_host_list().get_host(self.host_name)
        return host.get_administrative()

    def _get_db_node_cpu_sets(self, ssh_connection: SSHConnection) -> dict[int, frozenset[int]]:
        """Return per-NUMA-node CPU sets as recorded in the sysinv DB.

        Runs the ``i_icpu`` query via :class:`PostgresqlKeywords` and parses
        it with :class:`IcpuNumaCpuOutput`, which expands each node's CPUs
        into a set (0-based node ids) so the result can be compared directly
        against the OS sysfs mapping from
        :meth:`SysfsNumaKeywords.get_node_cpu_sets`.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.

        Returns:
            dict[int, frozenset[int]]: Mapping of node id (0-based) to its
            set of CPU ids.
        """
        query = "SELECT forinodeid, cpu FROM i_icpu ORDER BY forinodeid, cpu;"
        raw = PostgresqlKeywords(ssh_connection).query_database("sysinv", query)
        return IcpuNumaCpuOutput(raw).get_node_cpu_sets()

    def _wait_for_platform_services(self, ssh_connection: SSHConnection) -> None:
        """Wait until the StarlingX control plane answers on the given SSH session.

        Polls ``fm alarm-list`` until it returns successfully. While the host
        is still booting (or its platform services are not yet up) this call
        fails (e.g. "credentials can only be loaded from the active
        controller"), so a clean return is our signal that unlock_host's
        pre-checks will pass. This works even while the host is locked,
        unlike PowerKeywords.is_powered_on() (whose health gate requires
        administrative == 'unlocked').

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.

        Raises:
            Exception: If the control plane does not answer within
                PLATFORM_READY_WAIT_SECONDS.
        """
        deadline = time.time() + self.PLATFORM_READY_WAIT_SECONDS
        last_error = None
        while time.time() < deadline:
            try:
                AlarmListKeywords(ssh_connection).alarm_list()
                get_logger().log_info("StarlingX control plane is answering (fm alarm-list succeeded)")
                return
            except Exception as ex:  # noqa: BLE001 - control plane is expected to be down briefly after boot
                last_error = ex
                get_logger().log_info(f"Control plane not ready yet; retrying in {self.POST_RESET_POLL_INTERVAL_SECONDS}s")
                time.sleep(self.POST_RESET_POLL_INTERVAL_SECONDS)
        raise Exception(f"StarlingX control plane did not become ready within {self.PLATFORM_READY_WAIT_SECONDS}s (last error: {last_error})")

    def _wait_for_ssh_back(self) -> None:
        """Poll until an SSH connection to the host succeeds again after a reboot.

        Raises:
            Exception: If the host does not become SSH-reachable within
                SSH_BACK_WAIT_SECONDS.
        """
        deadline = time.time() + self.SSH_BACK_WAIT_SECONDS
        last_error = None
        # Give the host a head start: after a reset it is briefly still
        # SSH-reachable on the old session before it actually goes down, so
        # wait one poll interval before the first probe.
        time.sleep(self.POST_RESET_POLL_INTERVAL_SECONDS)
        while time.time() < deadline:
            try:
                ssh = self._get_ssh()
                ssh.send("uptime")
                get_logger().log_info(f"{self.host_name} is SSH-reachable again after reset")
                return
            except Exception as ex:  # noqa: BLE001 - reconnect is expected to fail while rebooting
                last_error = ex
                time.sleep(self.POST_RESET_POLL_INTERVAL_SECONDS)
        raise Exception(f"{self.host_name} did not become SSH-reachable within {self.SSH_BACK_WAIT_SECONDS}s after reset (last error: {last_error})")
