"""Validate a subcloud is at a healthy factory-installed baseline.

Factory readiness is checked on the subcloud directly -- SSH to its factory IP,
confirm the factory-install marker, and validate cluster health -- rather than
through the system controller's dcmanager deploy_status. That matters after a
factory restore: depending on the restore mode and the BMC's SEL support, a
successful factory restore can leave dcmanager reporting 'factory-restore-complete'
OR 'install-failed' (the SEL monitor times out on no-SEL/OpenBMC systems even when
the restore actually succeeded). Checking the subcloud itself is therefore the
reliable success signal, and it is the same check used as the pre-enroll precondition.
"""

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords

# Marker file the factory install writes when it finishes; its presence is what
# distinguishes a factory-installed subcloud from a merely reachable one.
FACTORY_INSTALL_COMPLETE_MARKER = "/var/lib/factory-install/complete"


class SubcloudFactoryReadyKeywords(BaseKeyword):
    """Validates a subcloud is factory-installed, reachable and healthy."""

    def validate_subcloud_factory_ready(self, subcloud_name: str) -> None:
        """Validate the subcloud is factory-installed, reachable and healthy.

        Connects to the subcloud at its factory IP with the factory credentials,
        confirms the factory-install-complete marker exists, and validates cluster
        health (alarms clear, pods/apps healthy). Used both as the pre-enroll
        precondition and as the success check after a factory restore.

        Args:
            subcloud_name (str): Subcloud to validate.

        Raises:
            Exception: If the subcloud is unreachable at its factory IP, the
                factory-install marker is missing, or the cluster is unhealthy.
        """
        get_logger().log_info(f"Connect to {subcloud_name} at its factory IP and verify factory-install")
        subcloud_ssh = LabConnectionKeywords().get_subcloud_factory_ssh(subcloud_name)

        validate_equals(FileKeywords(subcloud_ssh).file_exists(FACTORY_INSTALL_COMPLETE_MARKER), True, f"{subcloud_name} has {FACTORY_INSTALL_COMPLETE_MARKER} (factory-installed)")

        get_logger().log_info(f"Verify {subcloud_name} cluster is healthy")
        HealthKeywords(subcloud_ssh).validate_healty_cluster()
