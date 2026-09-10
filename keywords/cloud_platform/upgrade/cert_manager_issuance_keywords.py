import time

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.get_resource.kubectl_get_resource_keywords import KubectlGetResourceKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords


class CertManagerIssuanceKeywords(BaseKeyword):
    """
    This class contains the cert-manager certificate issuance check.

    The functional truth for cert-manager is that a certificate request is fulfilled end to end:
    the issuer signs it, the Certificate reaches Ready=True, and a kubernetes.io/tls secret is
    produced. Checking that the pods are running proves considerably less.

    A self-signed issuer is used, so there is no external CA, ACME, DNS, registry, CNI or hardware
    dependency and the check is deterministic on any system. Artifacts are created in a scratch
    namespace and removed afterwards.
    """

    PROBE_NAMESPACE = "stxtest-certmgr"
    # Issuance is asynchronous. A self-signed issuer normally completes in seconds, but the window
    # is generous because this also runs immediately after a platform upgrade or rollback, when the
    # controller is still settling.
    ISSUANCE_TIMEOUT = 120
    ISSUANCE_POLL_INTERVAL = 5
    # cert-manager validates its own resources through an admission webhook, and that webhook is
    # served by cert-manager's own pods. After a platform upgrade or rollback those pods are
    # recreated, and for a short window they are Running and Ready while the webhook is not yet
    # accepting connections - creating a Certificate then fails with "failed calling webhook ...
    # connection refused". Observed on hardware: the pods started 34 seconds before the resource was
    # applied and the webhook refused the connection. So applying the resources is retried for a
    # bounded window rather than failing on the first attempt.
    WEBHOOK_READY_TIMEOUT = 180
    WEBHOOK_POLL_INTERVAL = 10
    WEBHOOK_UNAVAILABLE_MARKERS = ("failed calling webhook", "connection refused")

    def __init__(self, ssh_connection: SSHConnection):
        """
        Instance of the class.

        Args:
            ssh_connection(SSHConnection): An instance of an SSH connection.

        """
        self.ssh_connection = ssh_connection
        self.create_namespace = KubectlCreateNamespacesKeywords(ssh_connection)
        self.delete_namespace = KubectlDeleteNamespaceKeywords(ssh_connection)
        self.yaml = YamlKeywords(ssh_connection)
        self.file_apply = KubectlFileApplyKeywords(ssh_connection)
        self.files = FileKeywords(ssh_connection)
        self.resources = KubectlGetResourceKeywords(ssh_connection)
        # One instance serves every phase of a test, so cleanup is tracked per phase.
        self._cleaned_up_phases = set()

    def validate_certificate_is_issued(self, request, phase: str) -> None:
        """
        Assert cert-manager issues a self-signed certificate and produces its TLS secret.

        The scratch namespace is removed as the last act of the check rather than being left for a
        test-level finalizer. A certificate left in place raises the platform's certificate-expiry
        alarm (500.200), and an open alarm makes 'software deploy start' refuse to proceed with "No
        alarms: [Fail]", so a check that leaves its artifacts behind blocks the very upgrade the
        test exists to exercise. A finalizer is registered as well, so the namespace is still
        removed if an assertion fails part-way through.

        Both the status condition and the artifact are checked. A Certificate can report Ready
        before its secret exists, and a secret of the wrong type would mean the issuance did not
        actually complete, so neither alone is sufficient.

        Args:
            request: pytest FixtureRequest, used to register cleanup for the failure path.
            phase(str): where in the upgrade this check is running, used to name artifacts so
                repeated runs do not overwrite each other, for example "pre" or "post-upgrade".

        """
        self.delete_namespace.cleanup_namespace(self.PROBE_NAMESPACE)
        # Registered per phase, and skipped when that phase already cleaned up on its happy path.
        # Cleanup state is tracked per phase rather than in one attribute because a single keyword
        # instance serves every phase of a test: a later phase resetting a shared flag would make
        # an earlier phase's finalizer believe its namespace still existed and delete it again,
        # logging the misleading error this tracking exists to prevent.
        request.addfinalizer(self._cleanup_finalizer(phase))
        self.create_namespace.create_namespaces(self.PROBE_NAMESPACE)

        issuer_name = f"stxtest-selfsigned-{phase}"
        cert_name = f"stxtest-cert-{phase}"
        secret_name = f"stxtest-cert-tls-{phase}"
        cert_template = get_stx_resource_path("resources/cloud_platform/app_compat/cert_manager/issuer-and-cert.yaml")
        cert_file = self.yaml.generate_yaml_file_from_template(
            cert_template,
            {
                "namespace": self.PROBE_NAMESPACE,
                "issuer_name": issuer_name,
                "cert_name": cert_name,
                "secret_name": secret_name,
            },
            f"cert-manager-issuance-{phase}.yaml",
            "/tmp",
        )
        self._apply_awaiting_webhook(cert_file, phase)

        def _certificate_ready() -> str:
            return self.resources.get_resource_field(
                "certificate",
                cert_name,
                '{.status.conditions[?(@.type=="Ready")].status}',
                namespace=self.PROBE_NAMESPACE,
            )

        validate_equals_with_retry(
            _certificate_ready,
            "True",
            f"[{phase}] cert-manager must issue the certificate (Certificate Ready=True)",
            timeout=self.ISSUANCE_TIMEOUT,
            polling_sleep_time=self.ISSUANCE_POLL_INTERVAL,
        )

        secret_type = self.resources.get_resource_field(
            "secret", secret_name, "{.type}", namespace=self.PROBE_NAMESPACE
        )
        validate_equals(
            secret_type,
            "kubernetes.io/tls",
            f"[{phase}] cert-manager must produce a kubernetes.io/tls secret",
        )

        # Remove the artifacts now rather than at test teardown. The issued certificate is
        # deliberately short-lived, so leaving it in place raises the platform's
        # certificate-expiry alarm and any open alarm blocks 'software deploy start'.
        self.delete_namespace.cleanup_namespace(self.PROBE_NAMESPACE)
        self._mark_cleaned_up(phase)
        self._remove_generated_file(cert_file)

    def _cleanup_finalizer(self, phase: str):
        """
        Return a finalizer that removes the scratch namespace unless this phase already did.

        Args:
            phase(str): the phase the finalizer belongs to.

        Returns:
            callable: the finalizer to register.

        """

        def _finalizer() -> None:
            if phase not in self._cleaned_up_phases:
                self.delete_namespace.cleanup_namespace(self.PROBE_NAMESPACE)

        return _finalizer

    def _mark_cleaned_up(self, phase: str) -> None:
        """
        Record that a phase removed its own artifacts, so its finalizer becomes a no-op.

        Args:
            phase(str): the phase that cleaned up.

        """
        self._cleaned_up_phases.add(phase)

    def _remove_generated_file(self, remote_path: str) -> None:
        """
        Delete a templated file this check wrote onto the system under test.

        Best effort: a leftover file is untidy but not a test failure, and reporting one would
        replace a real result with a housekeeping error.

        Args:
            remote_path(str): path on the controller to remove.

        """
        try:
            self.files.delete_file(remote_path)
        except Exception as delete_error:  # noqa: BLE001 - housekeeping must not fail the test
            get_logger().log_info(f"Could not remove {remote_path}: {delete_error}")

    def _apply_awaiting_webhook(self, resource_file: str, phase: str) -> None:
        """
        Apply the issuance resources, waiting out a cert-manager webhook that is still starting.

        cert-manager validates its own resources through an admission webhook served by its own
        pods. After a platform upgrade or rollback those pods are recreated, and there is a window
        in which they report Running and Ready while the webhook is not yet accepting connections.
        An apply in that window fails with "failed calling webhook ... connection refused", which
        says nothing about whether cert-manager works - only that it was asked too early.

        Only the webhook-unavailable signature is retried. Any other error fails immediately, so a
        cert-manager that is broken in some other way is reported at once rather than after the full
        window. A cert-manager that is permanently unreachable produces this same signature, so that
        case is reported when the window expires rather than immediately - the trade for not failing
        a healthy system that was merely asked too early.

        Args:
            resource_file(str): path on the controller to the templated resource file.
            phase(str): where in the upgrade this is running, for the failure message.

        Raises:
            KeywordException: when the webhook does not become available within the timeout.

        """
        deadline = time.time() + self.WEBHOOK_READY_TIMEOUT
        last_error = ""
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            output = self.file_apply.kubectl_apply_with_error(resource_file)
            if self.ssh_connection.get_return_code() == 0:
                if attempt > 1:
                    get_logger().log_info(
                        f"[{phase}] cert-manager webhook became available on attempt {attempt}"
                    )
                return
            last_error = output
            if not all(marker in output for marker in self.WEBHOOK_UNAVAILABLE_MARKERS):
                # Not the webhook still starting up: report it now rather than retrying a real error.
                break
            get_logger().log_info(
                f"[{phase}] cert-manager admission webhook is not accepting connections yet; "
                f"retrying in {self.WEBHOOK_POLL_INTERVAL}s"
            )
            time.sleep(self.WEBHOOK_POLL_INTERVAL)

        raise KeywordException(
            f"[{phase}] could not create the cert-manager issuance resources: {last_error}"
        )
