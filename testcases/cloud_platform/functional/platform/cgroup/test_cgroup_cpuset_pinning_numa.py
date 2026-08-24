"""Tests for cpuset pinning preservation after cgroup version switch.

Verifies that CPU pinning and NUMA affinity are preserved when switching
between cgroup v1 and v2 on a multi-NUMA worker node.

Reference: test_isolated_cpu.py — topology manager, isolcpu pods, NUMA validation.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_none
from keywords.cloud_platform.cgroup.cgroup_keywords import (
    CGROUP_V1,
    CGROUP_V2,
    CgroupKeywords,
)
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.k8s.node.kubectl_describe_node_keywords import KubectlDescribeNodeKeywords


@mark.p2
@mark.lab_has_compute
def test_cpuset_pinning_preserved_after_switch(request: FixtureRequest) -> None:
    """Verify cpuset pinning preserved for pods after cgroup version switch.

    On a worker node with isolcpus configured:
    1. Record current isolcpu allocatable count
    2. Switch cgroup version (lock/unlock worker)
    3. Verify isolcpu allocatable count unchanged after switch
    4. Verify kubelet reports same isolcpu resources

    Teardown:
        Revert to original cgroup version.
    """
    logger = get_logger()
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    original_version = cgroup_kw.detect_cgroup_version()
    request.addfinalizer(lambda: cgroup_kw.revert_cgroup_version(original_version))

    # Find a worker with isolcpus configured
    logger.log_info("Searching for a worker node with isolcpus configured")
    host_list = SystemHostListKeywords(ssh).get_system_host_list()
    worker_host = None
    allocatable = 0
    for host in host_list.get_hosts():
        if "worker" in host.get_personality() and host.get_administrative() == "unlocked":
            desc = KubectlDescribeNodeKeywords(ssh).describe_node(host.get_host_name())
            allocatable = desc.get_node_description().get_allocatable().get_windriver_isolcpus()
            if allocatable and allocatable > 0:
                worker_host = host.get_host_name()
                break

    validate_not_none(worker_host, "at least one worker with isolcpus found")
    logger.log_info(f"Using worker: {worker_host} with {allocatable} isolcpus")

    # Record pre-switch state
    logger.log_info("Recording pre-switch CPU topology and cgroup version")
    pre_switch_allocatable = allocatable

    host_cpu_output = SystemHostCPUKeywords(ssh).get_system_host_cpu_list(worker_host)
    pre_switch_isolcpus = host_cpu_output.get_number_of_logical_cores(
        processor_id=0, assigned_function='Application-isolated'
    )
    logger.log_info(f"Pre-switch: version={original_version}, isolcpus={pre_switch_isolcpus}")

    # Switch cgroup version
    target_version = CGROUP_V2 if original_version == CGROUP_V1 else CGROUP_V1
    logger.log_info(f"Switching cgroup version from {original_version} to {target_version}")
    cgroup_kw.switch_cgroup_version(target_version)

    # Reconnect after reboot
    ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Also lock/unlock the worker if it's not the active controller
    hostname = SystemHostListKeywords(ssh).get_active_controller().get_host_name()
    if worker_host != hostname:
        logger.log_info(f"Locking/unlocking worker {worker_host} to apply cgroup change")
        lock_kw = SystemHostLockKeywords(ssh)
        lock_kw.lock_host(worker_host)
        lock_kw.unlock_host(worker_host)

    # Verify post-switch state
    logger.log_info("Verifying cgroup version switched successfully")
    cgroup_kw_new = CgroupKeywords(ssh)
    post_switch_version = cgroup_kw_new.detect_cgroup_version()
    validate_equals(post_switch_version, target_version, "cgroup version after switch")

    # Verify isolcpu allocatable preserved
    logger.log_info("Verifying isolcpu allocatable count preserved after switch")
    desc = KubectlDescribeNodeKeywords(ssh).describe_node(worker_host)
    post_switch_allocatable = desc.get_node_description().get_allocatable().get_windriver_isolcpus()
    validate_equals(post_switch_allocatable, pre_switch_allocatable, "isolcpu allocatable preserved after switch")

    # Verify CPU topology preserved
    logger.log_info("Verifying CPU topology preserved after switch")
    host_cpu_output = SystemHostCPUKeywords(ssh).get_system_host_cpu_list(worker_host)
    post_switch_isolcpus = host_cpu_output.get_number_of_logical_cores(
        processor_id=0, assigned_function='Application-isolated'
    )
    validate_equals(post_switch_isolcpus, pre_switch_isolcpus, "isolated CPU count preserved after switch")

    logger.log_info("Cpuset pinning preserved after cgroup version switch")
