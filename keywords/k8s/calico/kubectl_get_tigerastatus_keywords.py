"""Keywords for the 'kubectl get tigerastatus' command."""

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals_with_retry
from keywords.k8s.calico.object.tigerastatus_output import TigeraStatusOutput
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword

TIGERASTATUS_HEALTHY_TIMEOUT_SECONDS = 120
TIGERASTATUS_POLLING_SECONDS = 10


class KubectlGetTigeraStatusKeywords(K8sBaseKeyword):
    """Class for the 'kubectl get tigerastatus' keyword."""

    def get_tigerastatus(self) -> TigeraStatusOutput:
        """Get the calico TigeraStatus as a parsed output object.

        Returns:
            TigeraStatusOutput: An object containing the parsed TigeraStatus conditions.
        """
        get_logger().log_debug("Getting the calico TigeraStatus")
        output = self.ssh_connection.send(self.k8s_config.export("kubectl get tigerastatus calico -o yaml"))
        self.validate_success_return_code(self.ssh_connection)
        return TigeraStatusOutput(output)

    def validate_healthy(self, timeout: int = TIGERASTATUS_HEALTHY_TIMEOUT_SECONDS, polling_sleep_time: int = TIGERASTATUS_POLLING_SECONDS) -> None:
        """Wait until the calico TigeraStatus reports a healthy operator.

        A healthy operator reports Available=True, Degraded=False and Progressing=False. The
        status is polled because the operator briefly reports Degraded while it reconciles, for
        example while a calico-node pod is Running but not yet Ready after a node recovers.

        Args:
            timeout (int): Seconds to wait for a healthy status.
            polling_sleep_time (int): Seconds between polls.
        """

        def get_unhealthy_conditions() -> list[str]:
            return self.get_tigerastatus().get_unhealthy_conditions()

        validate_equals_with_retry(
            function_to_execute=get_unhealthy_conditions,
            expected_value=[],
            validation_description="TigeraStatus reports no unhealthy condition (Available=True, Degraded=False, Progressing=False)",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )
