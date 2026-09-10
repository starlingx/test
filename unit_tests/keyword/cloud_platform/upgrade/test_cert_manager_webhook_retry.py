"""Unit tests for CertManagerIssuanceKeywords webhook handling.

Cover the case that failed on hardware: cert-manager's admission webhook is served by its own pods,
so immediately after a platform rollback those pods can be Running and Ready while the webhook is not
yet accepting connections. Applying the issuance resources then fails with "failed calling webhook
... connection refused", which says nothing about whether cert-manager works.
"""
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.upgrade.cert_manager_issuance_keywords import CertManagerIssuanceKeywords

WEBHOOK_ERROR = (
    'Error from server (InternalError): error when creating "/tmp/cert.yaml": Internal error '
    'occurred: failed calling webhook "webhook.cert-manager.io": failed to call webhook: '
    'Post "https://cm-cert-manager-webhook.cert-manager.svc:443/validate?timeout=30s": '
    "dial tcp 10.110.252.54:443: connect: connection refused"
)
OTHER_ERROR = 'Error from server (Forbidden): error when creating "/tmp/cert.yaml": forbidden'


class TestCertManagerWebhookRetry(unittest.TestCase):
    """Test suite for waiting out a cert-manager webhook that is still starting."""

    def setUp(self):
        """Silence the loggers and remove the sleep between attempts."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()
        self.module_logger_patcher = patch(
            "keywords.cloud_platform.upgrade.cert_manager_issuance_keywords.get_logger"
        )
        self.module_logger_patcher.start()
        self.sleep_patcher = patch("keywords.cloud_platform.upgrade.cert_manager_issuance_keywords.time.sleep")
        self.sleep_patcher.start()

    def tearDown(self):
        """Stop the patchers."""
        self.logger_patcher.stop()
        self.module_logger_patcher.stop()
        self.sleep_patcher.stop()

    def _build_keywords(self, outputs, return_codes):
        """Return an instance whose apply returns the given outputs and return codes in order.

        BaseKeyword.__getattribute__ wraps every callable attribute in a logging wrapper, so
        collaborators are installed with object.__setattr__ and built from NonCallableMagicMock to
        keep that wrapper from replacing them.

        Args:
            outputs (list): output string per apply attempt.
            return_codes (list): return code per apply attempt.

        Returns:
            tuple: (keywords, file_apply mock)
        """
        keywords = CertManagerIssuanceKeywords.__new__(CertManagerIssuanceKeywords)

        file_apply = NonCallableMagicMock()
        file_apply.kubectl_apply_with_error = MagicMock(side_effect=list(outputs))

        ssh = NonCallableMagicMock()
        ssh.get_return_code = MagicMock(side_effect=list(return_codes))

        object.__setattr__(keywords, "ssh_connection", ssh)
        object.__setattr__(keywords, "file_apply", file_apply)
        return keywords, file_apply

    def test_apply_succeeds_first_time(self):
        """A webhook that is already serving needs one attempt."""
        keywords, file_apply = self._build_keywords([""], [0])

        keywords._apply_awaiting_webhook("/tmp/cert.yaml", "pre")

        self.assertEqual(file_apply.kubectl_apply_with_error.call_count, 1)

    def test_apply_retries_while_the_webhook_is_starting(self):
        """A webhook that is not yet accepting connections is waited out, then the apply succeeds."""
        keywords, file_apply = self._build_keywords([WEBHOOK_ERROR, WEBHOOK_ERROR, ""], [1, 1, 0])

        keywords._apply_awaiting_webhook("/tmp/cert.yaml", "post-rollback")

        self.assertEqual(file_apply.kubectl_apply_with_error.call_count, 3)

    def test_apply_does_not_retry_an_unrelated_error(self):
        """Any error other than the webhook starting up fails at once, not after the full window."""
        keywords, file_apply = self._build_keywords([OTHER_ERROR], [1])

        with self.assertRaises(KeywordException) as raised:
            keywords._apply_awaiting_webhook("/tmp/cert.yaml", "pre")

        self.assertEqual(file_apply.kubectl_apply_with_error.call_count, 1)
        self.assertIn("forbidden", str(raised.exception))

    def test_apply_gives_up_and_reports_the_webhook_error(self):
        """A webhook that never answers is a real failure and is reported as such."""
        keywords, file_apply = self._build_keywords([WEBHOOK_ERROR] * 3, [1] * 3)
        # The clock is driven explicitly rather than relying on wall time: sleep is patched out, so
        # a short real timeout would spin thousands of times before expiring. These values give the
        # deadline, then two attempts inside the window, then a time past it.
        with patch(
            "keywords.cloud_platform.upgrade.cert_manager_issuance_keywords.time.time",
            side_effect=[0, 1, 2, 999],
        ):
            with self.assertRaises(KeywordException) as raised:
                keywords._apply_awaiting_webhook("/tmp/cert.yaml", "post-rollback")

        self.assertEqual(file_apply.kubectl_apply_with_error.call_count, 2)
        self.assertIn("failed calling webhook", str(raised.exception))
        self.assertIn("post-rollback", str(raised.exception))

    def test_each_phase_cleans_up_independently(self):
        """A later phase failing must not make an earlier phase's finalizer clean up again.

        One keyword instance serves all three phases of a test and each phase registers its own
        finalizer, so cleanup state cannot be tracked in a single instance attribute: phase 2
        resetting it would make phase 1's finalizer believe its namespace is still present and
        issue a redundant delete, which is the misleading error the tracking exists to prevent.
        """
        keywords, _ = self._build_keywords([""], [0])
        object.__setattr__(keywords, "_cleaned_up_phases", set())
        delete_namespace = NonCallableMagicMock()
        object.__setattr__(keywords, "delete_namespace", delete_namespace)

        # Phase 1 completes and cleans up.
        keywords._mark_cleaned_up("pre")
        # Phase 2 begins; its own cleanup has not happened yet.
        phase_two_finalizer = keywords._cleanup_finalizer("post-upgrade")
        # Phase 1's finalizer now runs at teardown. Its phase was already cleaned up, so it must
        # do nothing even though a later phase is outstanding.
        keywords._cleanup_finalizer("pre")()

        self.assertEqual(delete_namespace.cleanup_namespace.call_count, 0)

        # Phase 2 never cleaned up, so its finalizer must still act.
        phase_two_finalizer()
        self.assertEqual(delete_namespace.cleanup_namespace.call_count, 1)

    def test_the_check_registers_a_per_phase_finalizer_and_removes_its_file(self):
        """The production path must wire up per-phase cleanup and file removal, not just offer them.

        Written because reverting either wiring - registering one shared finalizer instead of a
        per-phase one, or dropping the file removal - left every other test in this file passing.
        Testing the helpers in isolation proves they work, not that they are used.
        """
        keywords, _ = self._build_keywords([""], [0])
        request = NonCallableMagicMock()
        request.addfinalizer = MagicMock()
        file_keywords = NonCallableMagicMock()
        yaml_keywords = NonCallableMagicMock()
        yaml_keywords.generate_yaml_file_from_template = MagicMock(
            return_value="/tmp/cert-manager-issuance-pre.yaml"
        )
        object.__setattr__(keywords, "files", file_keywords)
        object.__setattr__(keywords, "yaml", yaml_keywords)
        object.__setattr__(keywords, "create_namespace", NonCallableMagicMock())
        object.__setattr__(keywords, "delete_namespace", NonCallableMagicMock())
        object.__setattr__(keywords, "_cleaned_up_phases", set())
        resources = NonCallableMagicMock()
        resources.get_resource_field = MagicMock(side_effect=["True", "kubernetes.io/tls"])
        object.__setattr__(keywords, "resources", resources)
        object.__setattr__(keywords, "_apply_awaiting_webhook", MagicMock())

        with patch(
            "keywords.cloud_platform.upgrade.cert_manager_issuance_keywords.get_stx_resource_path",
            return_value="/resources/issuer-and-cert.yaml",
        ):
            with patch(
                "keywords.cloud_platform.upgrade.cert_manager_issuance_keywords.validate_equals_with_retry"
            ):
                with patch("keywords.cloud_platform.upgrade.cert_manager_issuance_keywords.validate_equals"):
                    keywords.validate_certificate_is_issued(request, "pre")

        # The phase that just ran is recorded, so its own finalizer will not delete again.
        self.assertIn("pre", keywords._cleaned_up_phases)
        # A finalizer was registered, and it is specific to this phase: it must no-op now.
        request.addfinalizer.assert_called_once()
        registered = request.addfinalizer.call_args[0][0]
        keywords.delete_namespace.cleanup_namespace.reset_mock()
        registered()
        self.assertEqual(keywords.delete_namespace.cleanup_namespace.call_count, 0)
        # The templated file written for this phase was removed.
        file_keywords.delete_file.assert_called_once_with("/tmp/cert-manager-issuance-pre.yaml")
        # The secret type is read through the shared resource keyword rather than a bypass, so that
        # read cannot be dropped unnoticed. The certificate-ready read runs inside the retry helper,
        # which is patched here; it is exercised by test_certificate_ready_is_read_via_the_resource_keyword.
        secret_reads = [c for c in resources.get_resource_field.call_args_list if c.args[0] == "secret"]
        self.assertEqual(len(secret_reads), 1)

    def test_certificate_ready_is_read_via_the_resource_keyword(self):
        """The certificate Ready condition is read through the shared resource keyword.

        This read runs inside validate_equals_with_retry, so the finalizer/cleanup test patches it
        out and cannot see it. Here the retry is real but resolves on the first poll, so the read
        actually fires and its bypass would be caught.
        """
        keywords, _ = self._build_keywords([""], [0])
        resources = NonCallableMagicMock()
        resources.get_resource_field = MagicMock(side_effect=["True", "kubernetes.io/tls"])
        request = NonCallableMagicMock()
        request.addfinalizer = MagicMock()
        yaml_keywords = NonCallableMagicMock()
        yaml_keywords.generate_yaml_file_from_template = MagicMock(return_value="/tmp/cert.yaml")
        object.__setattr__(keywords, "resources", resources)
        object.__setattr__(keywords, "yaml", yaml_keywords)
        object.__setattr__(keywords, "files", NonCallableMagicMock())
        object.__setattr__(keywords, "create_namespace", NonCallableMagicMock())
        object.__setattr__(keywords, "delete_namespace", NonCallableMagicMock())
        object.__setattr__(keywords, "_cleaned_up_phases", set())
        object.__setattr__(keywords, "_apply_awaiting_webhook", MagicMock())

        with patch(
            "keywords.cloud_platform.upgrade.cert_manager_issuance_keywords.get_stx_resource_path",
            return_value="/resources/issuer-and-cert.yaml",
        ):
            with patch("keywords.cloud_platform.upgrade.cert_manager_issuance_keywords.validate_equals"):
                # Run the retry helper for real to the extent of calling its function once, so the
                # certificate-ready read actually fires rather than being skipped by a full patch.
                with patch(
                    "keywords.cloud_platform.upgrade.cert_manager_issuance_keywords.validate_equals_with_retry",
                    side_effect=lambda fn, *a, **k: fn(),
                ):
                    keywords.validate_certificate_is_issued(request, "pre")

        read_types = [c.args[0] for c in resources.get_resource_field.call_args_list]
        self.assertEqual(read_types, ["certificate", "secret"])

    def test_templated_files_are_removed_after_the_check(self):
        """The per-phase YAML written to the controller is deleted, not left behind.

        The check writes a templated file per phase onto the system under test. Leaving them
        accumulates litter on a filesystem whose size the upgrade itself is sensitive to.
        """
        keywords, _ = self._build_keywords([""], [0])
        file_keywords = NonCallableMagicMock()
        object.__setattr__(keywords, "files", file_keywords)

        keywords._remove_generated_file("/tmp/cert-manager-issuance-pre.yaml")

        file_keywords.delete_file.assert_called_once_with("/tmp/cert-manager-issuance-pre.yaml")


if __name__ == "__main__":
    unittest.main()
