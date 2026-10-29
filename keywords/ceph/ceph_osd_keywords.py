import re

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.ceph.object.ceph_osd_tree_output import CephOsdTreeOutput


class CephOsdKeywords(BaseKeyword):
    """Keywords for inspecting and manipulating Ceph OSD runtime state."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to a host with Ceph CLI access.
        """
        self.ssh_connection = ssh_connection

    def get_ceph_osd_tree(self) -> CephOsdTreeOutput:
        """Run 'ceph osd tree' and return the parsed output.

        Returns:
            CephOsdTreeOutput: Parsed OSD tree with per-OSD status and host.
        """
        output = self.ssh_connection.send("ceph osd tree")
        self.validate_success_return_code(self.ssh_connection)
        return CephOsdTreeOutput(output)

    def wait_for_osds_down_for_host(self, host: str, timeout: int = 120, polling_sleep_time: int = 5) -> None:
        """Wait until all OSDs on a host report down.

        Args:
            host (str): The host name whose OSDs should go down.
            timeout (int): Maximum time to wait in seconds.
            polling_sleep_time (int): Time between checks in seconds.
        """
        validate_equals_with_retry(
            function_to_execute=lambda: self.get_ceph_osd_tree().are_all_osds_down_for_host(host),
            expected_value=True,
            validation_description=f"All OSDs on host '{host}' are down",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def wait_for_osds_up_for_host(self, host: str, timeout: int = 300, polling_sleep_time: int = 10) -> None:
        """Wait until all OSDs on a host report up.

        Args:
            host (str): The host name whose OSDs should come up.
            timeout (int): Maximum time to wait in seconds.
            polling_sleep_time (int): Time between checks in seconds.
        """
        validate_equals_with_retry(
            function_to_execute=lambda: self.get_ceph_osd_tree().are_all_osds_up_for_host(host),
            expected_value=True,
            validation_description=f"All OSDs on host '{host}' are up",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def wait_for_osd_up(self, osd_id: int, timeout: int = 300, polling_sleep_time: int = 10) -> None:
        """Wait until a single OSD reports up in 'ceph osd tree'.

        Args:
            osd_id (int): The OSD id to check (e.g. 1 for 'osd.1').
            timeout (int): Maximum time to wait in seconds.
            polling_sleep_time (int): Time between checks in seconds.
        """
        validate_equals_with_retry(
            function_to_execute=lambda: self.get_ceph_osd_tree().is_osd_up(osd_id),
            expected_value=True,
            validation_description=f"OSD osd.{osd_id} is up",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def wait_for_osd_down(self, osd_id: int, timeout: int = 120, polling_sleep_time: int = 5) -> None:
        """Wait until a single OSD reports down in 'ceph osd tree'.

        Args:
            osd_id (int): The OSD id to check (e.g. 1 for 'osd.1').
            timeout (int): Maximum time to wait in seconds.
            polling_sleep_time (int): Time between checks in seconds.
        """
        validate_equals_with_retry(
            function_to_execute=lambda: self.get_ceph_osd_tree().is_osd_up(osd_id),
            expected_value=False,
            validation_description=f"OSD osd.{osd_id} is down",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def mark_osd_out(self, osd_id: int) -> None:
        """Mark an OSD 'out' so CRUSH stops placing new/rebalanced data on it.

        This does not stop the OSD daemon by itself; pair it with scaling the
        OSD's rook-ceph deployment to 0 (see get_osd_deployment_name) to fully
        simulate a disk/daemon failure instead of a transient flap.

        Args:
            osd_id (int): The OSD id to mark out (e.g. 1 for 'osd.1').
        """
        self.ssh_connection.send(f"ceph osd out osd.{osd_id}")
        self.validate_success_return_code(self.ssh_connection)

    def mark_osd_in(self, osd_id: int) -> None:
        """Mark an OSD 'in', allowing CRUSH to place data on it again.

        Args:
            osd_id (int): The OSD id to mark in (e.g. 1 for 'osd.1').
        """
        self.ssh_connection.send(f"ceph osd in osd.{osd_id}")
        self.validate_success_return_code(self.ssh_connection)

    def get_osd_deployment_name(self, osd_id: int) -> str:
        """Get the rook-ceph Kubernetes Deployment name backing an OSD daemon.

        Follows rook-ceph's standard naming convention (namespace 'rook-ceph').

        Args:
            osd_id (int): The OSD id (e.g. 1 for 'osd.1').

        Returns:
            str: The Deployment name, e.g. 'rook-ceph-osd-1'.
        """
        return f"rook-ceph-osd-{osd_id}"

    def get_acting_osd_ids(self, pool_name: str, object_name: str) -> list[int]:
        """Get the acting OSD ids for the PG holding a given RADOS object.

        Runs 'ceph osd map <pool> <object>' and parses the 'acting ([...], pN)'
        portion of the output, proving which OSDs actually hold replicas of
        that object. Order reflects whatever Ceph reports; use 'pN' in the raw
        'ceph osd map' output separately if the primary specifically matters.

        Args:
            pool_name (str): The pool the object belongs to.
            object_name (str): The object name to map.

        Returns:
            list[int]: OSD ids in the acting set.

        Raises:
            KeywordException: If the acting set could not be parsed from the output.
        """
        output = self.ssh_connection.send(f"ceph osd map {pool_name} {object_name}")
        self.validate_success_return_code(self.ssh_connection)
        text = " ".join(output) if isinstance(output, list) else str(output)
        match = re.search(r"acting \(\[([0-9,]+)\]", text)
        if not match:
            raise KeywordException(f"Could not parse acting OSD set from 'ceph osd map {pool_name} {object_name}' output: {text}")
        return [int(osd_id) for osd_id in match.group(1).split(",")]
