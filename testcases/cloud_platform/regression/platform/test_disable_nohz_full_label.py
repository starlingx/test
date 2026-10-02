"""Tests for the disable-nohz-full host label controlling kernel nohz isolation args.

Verifies that the disable-nohz-full host label controls the kernel nohz
isolation arguments as expected on each kernel type.

The tests are KERNEL-ADAPTIVE: they do not switch the kernel. They detect the
kernel the lab is currently running and assert the expected behavior:
- Standard kernel : `disable-nohz-full=enabled` REMOVES the `nohz` token from
  `isolcpus=` and removes the `nohz_full=` grub arg (keeping CPUs isolated);
  removing the label RESTORES both.
- Lowlatency/RT   : the label has NO effect; `nohz_full=` persists regardless of
  the label being added or removed.

The nohz args only appear when CPUs are application-isolated; if the host has
none, the test isolates some during setup and restores the original CPU
allocation in teardown.

Config: AIO-SX (simplex). Marked lab_is_simplex only (no kernel capability) so the
tests run on whichever kernel the lab is on and adapt their assertions.

Host mutations are composed in the test from the existing single-purpose keywords:
SystemHostLockKeywords.lock_host / unlock_host wrap a mutate call
(SystemHostCPUKeywords.system_host_cpu_modify or
SystemHostLabelKeywords.system_host_label_assign / system_host_label_remove). Lock
and unlock are kept separate from the mutate so one lock/unlock wraps a single
change (one reboot) and could wrap several if ever needed. Inspection reads use the
existing keywords and Output objects directly (LabConnectionKeywords,
SystemHostCPUKeywords/SystemHostCPUOutput, SystemHostKernelKeywords/
SystemHostKernelShowObject, DisableNohzFullKeywords). Per-test state is local and
restoration is registered via request.addfinalizer (ACE rule: no fixtures).

WARNING: These tests lock/unlock the sole controller, causing reboots. Run only on
a lab dedicated to this verification.
"""

from pytest import FixtureRequest, fail, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.disable_nohz_full_keywords import DisableNohzFullKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_kernel_keywords import SystemHostKernelKeywords
from keywords.cloud_platform.system.host.system_host_label_keywords import SystemHostLabelKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords

APPLICATION_ISOLATED_FUNCTION = "Application-isolated"
APPLICATION_ISOLATED_CPU_FUNCTION = "application-isolated"

# Label under test
DISABLE_NOHZ_LABEL_KEY = "disable-nohz-full"
DISABLE_NOHZ_LABEL = "disable-nohz-full=enabled"

# Physical cores on processor 0 to isolate when a lab has none (so nohz args appear)
DEFAULT_ISOLATED_PHYSICAL_CORES = 2

# Config-out-of-date alarm tolerated during the lock/unlock reboot
CONFIG_OUT_OF_DATE_ALARM = "250.001"

# Longer unlock-accept timeout used for reboots triggered by host modifications
UNLOCK_ACCEPTED_TIMEOUT = 3000


def _prepare(request: FixtureRequest) -> str:
    """Ensure the active controller is ready for a nohz-label test and register cleanup.

    The nohz isolation args (isolcpus=nohz / nohz_full=) only appear when CPUs are
    application-isolated. If the host has none, this isolates some as part of setup
    so the test is self-sufficient on any lab. Captures the original isolated-core
    count and label state and registers finalizers to restore both, so the lab is
    returned to its starting state even if a step is interrupted.

    Args:
        request (FixtureRequest): pytest request object for addfinalizer.

    Returns:
        str: The active controller host name.
    """
    get_logger().log_setup_step("Connect to active controller and read lab state")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    host_name = SystemHostListKeywords(ssh_connection).get_active_controller().get_host_name()

    get_logger().log_setup_step("Ensure application-isolated CPUs exist (isolate if none)")
    original_isolated_physical = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(host_name).get_number_of_physical_cores(processor_id=0, assigned_function=APPLICATION_ISOLATED_FUNCTION)
    if original_isolated_physical == 0:
        lock_keywords = SystemHostLockKeywords(LabConnectionKeywords().get_active_controller_ssh())
        lock_keywords.lock_host(host_name)
        SystemHostCPUKeywords(lock_keywords.ssh_connection).system_host_cpu_modify(
            hostname=host_name, function=APPLICATION_ISOLATED_CPU_FUNCTION, num_cores_on_processor_0=DEFAULT_ISOLATED_PHYSICAL_CORES
        )
        lock_keywords.unlock_host(host_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT, exclude_alarm_ids=[CONFIG_OUT_OF_DATE_ALARM])

    # Restore the original isolated-core count on teardown (registered first so it
    # runs LAST, after the label is restored). Only reboots if the count changed.
    def _restore_cpus() -> None:
        get_logger().log_teardown_step("Restore original application-isolated CPU count")
        current_physical = SystemHostCPUKeywords(LabConnectionKeywords().get_active_controller_ssh()).get_system_host_cpu_list(host_name).get_number_of_physical_cores(processor_id=0, assigned_function=APPLICATION_ISOLATED_FUNCTION)
        if current_physical != original_isolated_physical:
            lock_keywords = SystemHostLockKeywords(LabConnectionKeywords().get_active_controller_ssh())
            lock_keywords.lock_host(host_name)
            SystemHostCPUKeywords(lock_keywords.ssh_connection).system_host_cpu_modify(
                hostname=host_name, function=APPLICATION_ISOLATED_CPU_FUNCTION, num_cores_on_processor_0=original_isolated_physical
            )
            lock_keywords.unlock_host(host_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT, exclude_alarm_ids=[CONFIG_OUT_OF_DATE_ALARM])

    request.addfinalizer(_restore_cpus)

    isolated_cpu_count = SystemHostCPUKeywords(LabConnectionKeywords().get_active_controller_ssh()).get_system_host_cpu_list(host_name).get_function_count(APPLICATION_ISOLATED_FUNCTION)
    if isolated_cpu_count == 0:
        fail("Failed to configure application-isolated CPUs; cannot verify nohz isolation args.")

    original_label_present = DisableNohzFullKeywords(LabConnectionKeywords().get_active_controller_ssh()).is_label_present(host_name)
    get_logger().log_setup_step(f"Lab state: host={host_name}, disable-nohz-full present={original_label_present}")

    # Register label-state restoration. Registered after the CPU-restore finalizer
    # so it runs FIRST on teardown. Recovers from an interrupted mid-lock state,
    # then only reboots if the current label state differs from the original.
    def _restore_label() -> None:
        get_logger().log_teardown_step("Recover host (unlock if needed) and restore label state")
        SystemHostLockKeywords(LabConnectionKeywords().get_active_controller_ssh()).ensure_host_unlocked(
            host_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT, exclude_alarm_ids=[CONFIG_OUT_OF_DATE_ALARM]
        )
        currently_present = DisableNohzFullKeywords(LabConnectionKeywords().get_active_controller_ssh()).is_label_present(host_name)
        if original_label_present and not currently_present:
            lock_keywords = SystemHostLockKeywords(LabConnectionKeywords().get_active_controller_ssh())
            lock_keywords.lock_host(host_name)
            SystemHostLabelKeywords(lock_keywords.ssh_connection).system_host_label_assign(host_name, DISABLE_NOHZ_LABEL, overwrite=True)
            lock_keywords.unlock_host(host_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT, exclude_alarm_ids=[CONFIG_OUT_OF_DATE_ALARM])
        elif not original_label_present and currently_present:
            lock_keywords = SystemHostLockKeywords(LabConnectionKeywords().get_active_controller_ssh())
            lock_keywords.lock_host(host_name)
            SystemHostLabelKeywords(lock_keywords.ssh_connection).system_host_label_remove(host_name, DISABLE_NOHZ_LABEL_KEY)
            lock_keywords.unlock_host(host_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT, exclude_alarm_ids=[CONFIG_OUT_OF_DATE_ALARM])

    request.addfinalizer(_restore_label)

    return host_name


@mark.p1
@mark.lab_is_simplex
def test_disable_nohz_full_baseline_has_nohz(request: FixtureRequest) -> None:
    """TC-01: Baseline — with no label, nohz isolation is present on either kernel.

    Setup:
        - Connect to active controller; require application-isolated CPUs.
        - Register label-state restoration finalizer.

    Test Steps:
        1. Ensure the disable-nohz-full label is absent.
        2. Read /proc/cmdline.

    Expected:
        - Label not present.
        - nohz_full= present.
        - On the standard kernel, isolcpus= also carries the 'nohz' token.

    Config: AIO-SX.
    """
    host_name = _prepare(request)
    kernel_show = SystemHostKernelKeywords(LabConnectionKeywords().get_active_controller_ssh()).get_system_host_kernel_show(host_name)
    is_rt = kernel_show.get_host_kernel_show().is_lowlatency()

    get_logger().log_test_case_step("Ensure disable-nohz-full label is absent")
    if DisableNohzFullKeywords(LabConnectionKeywords().get_active_controller_ssh()).is_label_present(host_name):
        lock_keywords = SystemHostLockKeywords(LabConnectionKeywords().get_active_controller_ssh())
        lock_keywords.lock_host(host_name)
        SystemHostLabelKeywords(lock_keywords.ssh_connection).system_host_label_remove(host_name, DISABLE_NOHZ_LABEL_KEY)
        lock_keywords.unlock_host(host_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT, exclude_alarm_ids=[CONFIG_OUT_OF_DATE_ALARM])

    get_logger().log_test_case_step("Verify baseline nohz isolation args are present")
    nohz_kw = DisableNohzFullKeywords(LabConnectionKeywords().get_active_controller_ssh())
    validate_equals(
        observed_value=nohz_kw.is_label_present(host_name),
        expected_value=False,
        validation_description="disable-nohz-full label absent at baseline",
    )
    validate_equals(
        observed_value=nohz_kw.get_proc_cmdline().has_nohz_full(),
        expected_value=True,
        validation_description="Baseline: cmdline contains nohz_full=",
    )
    if not is_rt:
        validate_equals(
            observed_value=nohz_kw.get_proc_cmdline().has_isolcpus_nohz(),
            expected_value=True,
            validation_description="Standard-kernel baseline: isolcpus contains 'nohz'",
        )


@mark.p1
@mark.lab_is_simplex
def test_disable_nohz_full_label_toggle(request: FixtureRequest) -> None:
    """TC-02 (CORE): enable then remove the label; verify nohz is toggled accordingly.

    Covers the full round-trip in one test to avoid redundant reboots.

    Setup:
        - Connect to active controller; ensure application-isolated CPUs exist.
        - Register CPU and label restoration finalizers.

    Test Steps:
        1. Ensure the label is absent and confirm baseline nohz is present.
        2. Enable disable-nohz-full and unlock (reboot); assert the label effect.
        3. Remove the label and unlock (reboot); assert the original state is restored.

    Expected:
        - Standard kernel:
            enable  -> 'nohz' removed from isolcpus= and nohz_full= removed (the fix),
                       isolated CPU count unchanged;
            remove  -> 'nohz' restored in isolcpus= and nohz_full= returns.
        - Lowlatency/RT kernel:
            nohz_full= persists throughout (label has no effect on either transition).

    Config: AIO-SX.
    """
    host_name = _prepare(request)
    kernel_show = SystemHostKernelKeywords(LabConnectionKeywords().get_active_controller_ssh()).get_system_host_kernel_show(host_name)
    is_rt = kernel_show.get_host_kernel_show().is_lowlatency()

    get_logger().log_test_case_step("Ensure label absent and confirm baseline nohz present")
    if DisableNohzFullKeywords(LabConnectionKeywords().get_active_controller_ssh()).is_label_present(host_name):
        lock_keywords = SystemHostLockKeywords(LabConnectionKeywords().get_active_controller_ssh())
        lock_keywords.lock_host(host_name)
        SystemHostLabelKeywords(lock_keywords.ssh_connection).system_host_label_remove(host_name, DISABLE_NOHZ_LABEL_KEY)
        lock_keywords.unlock_host(host_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT, exclude_alarm_ids=[CONFIG_OUT_OF_DATE_ALARM])
    nohz_kw = DisableNohzFullKeywords(LabConnectionKeywords().get_active_controller_ssh())
    validate_equals(nohz_kw.get_proc_cmdline().has_nohz_full(), True, "Precondition: nohz_full present before label")
    if not is_rt:
        validate_equals(nohz_kw.get_proc_cmdline().has_isolcpus_nohz(), True, "Precondition: nohz present in isolcpus before label")
    isolated_before = SystemHostCPUKeywords(LabConnectionKeywords().get_active_controller_ssh()).get_system_host_cpu_list(host_name).get_function_count(APPLICATION_ISOLATED_FUNCTION)

    get_logger().log_test_case_step("Enable disable-nohz-full and unlock (reboot)")
    lock_keywords = SystemHostLockKeywords(LabConnectionKeywords().get_active_controller_ssh())
    lock_keywords.lock_host(host_name)
    SystemHostLabelKeywords(lock_keywords.ssh_connection).system_host_label_assign(host_name, DISABLE_NOHZ_LABEL, overwrite=True)
    lock_keywords.unlock_host(host_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT, exclude_alarm_ids=[CONFIG_OUT_OF_DATE_ALARM])

    get_logger().log_test_case_step("Verify label-enabled effect per running kernel")
    nohz_kw = DisableNohzFullKeywords(LabConnectionKeywords().get_active_controller_ssh())
    validate_equals(
        observed_value=nohz_kw.is_label_present(host_name),
        expected_value=True,
        validation_description="disable-nohz-full label is set",
    )
    if is_rt:
        validate_equals(
            observed_value=nohz_kw.get_proc_cmdline().has_nohz_full(),
            expected_value=True,
            validation_description="RT kernel: nohz_full still present after label enabled (no effect)",
        )
    else:
        validate_equals(
            observed_value=nohz_kw.get_proc_cmdline().has_isolcpus_nohz(),
            expected_value=False,
            validation_description="Standard-kernel: 'nohz' removed from isolcpus after label enabled (fix)",
        )
        validate_equals(
            observed_value=nohz_kw.get_proc_cmdline().has_nohz_full(),
            expected_value=False,
            validation_description="Standard-kernel: nohz_full= removed from cmdline after label enabled (fix)",
        )
    validate_equals(
        observed_value=SystemHostCPUKeywords(LabConnectionKeywords().get_active_controller_ssh()).get_system_host_cpu_list(host_name).get_function_count(APPLICATION_ISOLATED_FUNCTION),
        expected_value=isolated_before,
        validation_description="Isolated CPUs preserved after label enabled",
    )

    get_logger().log_test_case_step("Remove disable-nohz-full and unlock (reboot)")
    lock_keywords = SystemHostLockKeywords(LabConnectionKeywords().get_active_controller_ssh())
    lock_keywords.lock_host(host_name)
    SystemHostLabelKeywords(lock_keywords.ssh_connection).system_host_label_remove(host_name, DISABLE_NOHZ_LABEL_KEY)
    lock_keywords.unlock_host(host_name, unlock_accepted_timeout=UNLOCK_ACCEPTED_TIMEOUT, exclude_alarm_ids=[CONFIG_OUT_OF_DATE_ALARM])

    get_logger().log_test_case_step("Verify label-removed restores original state per running kernel")
    nohz_kw = DisableNohzFullKeywords(LabConnectionKeywords().get_active_controller_ssh())
    validate_equals(
        observed_value=nohz_kw.is_label_present(host_name),
        expected_value=False,
        validation_description="disable-nohz-full label is removed",
    )
    if is_rt:
        validate_equals(
            observed_value=nohz_kw.get_proc_cmdline().has_nohz_full(),
            expected_value=True,
            validation_description="RT kernel: nohz_full still present after label removed (no effect)",
        )
    else:
        validate_equals(
            observed_value=nohz_kw.get_proc_cmdline().has_isolcpus_nohz(),
            expected_value=True,
            validation_description="Standard-kernel: 'nohz' restored in isolcpus after label removed",
        )
        validate_equals(
            observed_value=nohz_kw.get_proc_cmdline().has_nohz_full(),
            expected_value=True,
            validation_description="Standard-kernel: nohz_full= restored in cmdline after label removed",
        )
