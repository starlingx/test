"""Fresh policy enforcement evidence across platform release transitions."""

import re
from collections.abc import Callable
from functools import partial

from packaging.version import Version

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.applications.ipsec_policy_keywords import IPsecPolicyKeywords
from keywords.cloud_platform.applications.ipsec_policy_state_keywords import IPsecPolicyStateKeywords
from keywords.cloud_platform.applications.ipsec_policy_traffic_keywords import IPsecPolicyTrafficKeywords
from keywords.cloud_platform.applications.object.ipsec_policy_traffic_input import IPsecPolicyTrafficInput
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


class IPsecPolicyCompatibilityKeywords(BaseKeyword):
    """Use shared traffic, ownership and CHILD_SA checks in each phase."""

    def __init__(self, ssh_connection: SSHConnection):
        """Retain the controller used for policy operations.

        Args:
            ssh_connection (SSHConnection): Controller connection.
        """
        self.ssh_connection = ssh_connection
        self.policy = IPsecPolicyKeywords(ssh_connection)
        self.original_state = IPsecPolicyStateKeywords(ssh_connection)

    def capture_original_configuration(self) -> None:
        """Retain the original policies and user settings across all releases."""
        self.original_state.capture_baseline(exclusive=True)

    @staticmethod
    def normalize_platform_release(version: str) -> str:
        """Normalize a numeric platform release with an optional zero patch.

        Args:
            version (str): Platform release reported by system show.

        Returns:
            str: Release with any explicit zero patch removed.
        """
        if re.fullmatch(r"\d+\.\d+\.0", version):
            return version.rsplit(".", 1)[0]
        return version

    def validate_inputs(self, from_version: str, to_version: str, image: str) -> tuple[str, ...]:
        """Reject invalid release, image and topology inputs before mutation.

        Args:
            from_version (str): Installed platform release.
            to_version (str): Configured target release.
            image (str): Immutable Python-capable traffic image.

        Returns:
            tuple[str, ...]: Independently discovered eligible nodes.
        """
        if not all(re.fullmatch(r"\d+\.\d+", version) for version in (from_version, to_version)):
            raise KeywordException("Compatibility requires numeric major.minor releases")
        if Version(to_version) <= Version(from_version):
            raise KeywordException("Target release must be newer than the baseline")
        if not re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", image):
            raise KeywordException("Configure an immutable Python-capable traffic image")
        # An applied operator can still be propagating agent scheduling labels.
        self.policy.wait_for_agents_ready()
        nodes = tuple(sorted(self.policy.get_eligible_nodes().get_node_names()))
        if len(nodes) < 2:
            raise KeywordException("Policy enforcement requires two eligible nodes")
        return nodes

    def verify_enforcement(self, addfinalizer: Callable, phase: str, image: str, expected_nodes: tuple[str, ...]) -> None:
        """Verify fresh TCP and UDP traffic on policy-selected live tunnels.

        Each phase owns independent resources and cleans them before the next
        platform transition. Finalizers retain recovery for partial failures.
        Existing policies are captured and checked without modification.

        Args:
            addfinalizer (Callable): Test recovery registration function.
            phase (str): Evidence phase label.
            image (str): Immutable Python-capable traffic image.
            expected_nodes (tuple[str, ...]): Baseline eligible node coverage.
        """
        self.policy.wait_for_agents_ready()
        self.original_state.verify_configuration()
        validate_equals(tuple(sorted(self.policy.get_eligible_nodes().get_node_names())), expected_nodes, f"[{phase}] policy agent node coverage")
        get_logger().log_info(f"[{phase}] running policy images: {self.policy.get_running_images().get_log_summary()}")
        client = LabConnectionKeywords().get_ssh_for_hostname(expected_nodes[0])
        for protocol in ("tcp", "udp"):
            traffic = IPsecPolicyTrafficKeywords(self.ssh_connection)
            pending_cleanup: list[Callable[[], None]] = []

            restore_phase = partial(self._restore_phase, pending_cleanup)
            # Register before setup. Successful inline cleanup clears this phase's
            # callbacks so pytest cannot replay them after a release transition.
            addfinalizer(restore_phase)
            traffic.capture_state(pending_cleanup.append, exclusive=True)
            traffic.create_traffic_fixture(IPsecPolicyTrafficInput(image, expected_nodes[0], expected_nodes[1], protocol=protocol))
            traffic.create_service_policy()
            evidence = traffic.verify_policy_traffic(client)
            get_logger().log_info(f"[{phase}] {protocol} policy enforcement verified: nonce={evidence.get_traffic().get_nonce()}, associations={evidence.get_associations()}, before={evidence.get_before_counters()}, after={evidence.get_after_counters()}")
            restore_phase()

    def _restore_phase(self, pending_cleanup: list[Callable[[], None]]) -> None:
        """Run recovery callbacks in reverse order, retaining failed work.

        Args:
            pending_cleanup (list[Callable[[], None]]): This scenario's callbacks.
        """
        while pending_cleanup:
            pending_cleanup[-1]()
            pending_cleanup.pop()
