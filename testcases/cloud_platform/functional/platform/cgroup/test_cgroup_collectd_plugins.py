"""Tests for collectd plugins functionality with cgroup version.

Verifies collectd service is active and reporting metrics correctly
regardless of cgroup version.

Reference: gnss_monitoring_keywords.py — calls collectd CLI via SSH.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.linux.find.find_keywords import FindKeywords
from keywords.linux.grep.grep_keywords import GrepKeywords
from keywords.linux.pgrep.pgrep_keywords import PgrepKeywords
from keywords.linux.systemctl.systemctl_is_active_keywords import SystemCTLIsActiveKeywords


@mark.p2
def test_collectd_service_active() -> None:
    """Verify collectd service is active."""
    logger = get_logger()
    ssh = LabConnectionKeywords().get_active_controller_ssh()

    logger.log_info("Checking collectd service status")
    is_active_keywords = SystemCTLIsActiveKeywords(ssh)
    status = is_active_keywords.is_active("collectd")
    validate_equals(status, "active", "collectd service is active")


@mark.p2
def test_collectd_no_cgroup_errors_in_log() -> None:
    """Verify no cgroup-related errors in collectd log."""
    logger = get_logger()
    ssh = LabConnectionKeywords().get_active_controller_ssh()

    logger.log_info("Checking collectd log for cgroup-related errors")
    grep_keywords = GrepKeywords(ssh)
    count = grep_keywords.get_match_count(
        "cgroup.*error\\|error.*cgroup", "/var/log/collectd.log"
    )
    logger.log_info(f"Cgroup-related errors in collectd.log: {count}")
    validate_equals(count, 0, "no cgroup-related errors in collectd log")


@mark.p2
def test_collectd_metrics_reporting() -> None:
    """Verify collectd is reporting metrics (no stale data).

    Checks that collectd process is running and has recent activity
    in its log file.
    """
    logger = get_logger()
    ssh = LabConnectionKeywords().get_active_controller_ssh()

    logger.log_info("Checking collectd process is running")
    pgrep_keywords = PgrepKeywords(ssh)
    count = pgrep_keywords.get_process_count("collectd")
    logger.log_info(f"collectd process count: {count}")
    validate_greater_than(count, 0, "collectd process is running")

    logger.log_info("Checking collectd log has recent entries (within last 5 minutes)")
    find_keywords = FindKeywords(ssh)
    recently_modified = find_keywords.is_file_modified_within(
        "/var/log/collectd.log", minutes=5
    )
    logger.log_info(f"Collectd log modified in last 5 min: {recently_modified}")
    validate_equals(recently_modified, True, "collectd log recently updated")
