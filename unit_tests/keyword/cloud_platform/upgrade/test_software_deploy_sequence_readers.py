"""Unit tests for SoftwareDeploySequenceKeywords readers and guards.

Cover, without a lab: that an unreached deploy state raises rather than letting a run continue,
that an absent deploy reads as no state at all, that a short platform version resolves to the full
release ID USM requires, that an ambiguous version is rejected rather than guessed at, and that
the running release is read from the host rather than from the release table.
"""
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.upgrade.software_deploy_sequence_keywords import SoftwareDeploySequenceKeywords


class TestSoftwareDeploySequenceReaders(unittest.TestCase):
    """Test suite for the deploy-state reads, the state guard and release resolution."""

    def setUp(self):
        """Silence the BaseKeyword logging wrapper."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()

    def tearDown(self):
        """Stop the logger patcher."""
        self.logger_patcher.stop()

    def _build_keywords(self, deploy_state="", state_reached=True, releases=(), running="26.03"):
        """Return an instance whose USM, deploy-show, software-list and system-show are mocked.

        BaseKeyword.__getattribute__ wraps every callable attribute in a logging wrapper, so
        collaborators are installed with object.__setattr__ and built from NonCallableMagicMock to
        keep that wrapper from replacing them.

        Args:
            deploy_state (str): state reported by 'software deploy show'; "" means no deploy.
            state_reached (bool): what USMKeywords.wait_for_deploy_state returns.
            releases (tuple): release names reported by 'software list'.
            running (str): software version reported by 'system show'.

        Returns:
            SoftwareDeploySequenceKeywords: the instance under test.
        """
        keywords = SoftwareDeploySequenceKeywords.__new__(SoftwareDeploySequenceKeywords)

        usm = NonCallableMagicMock()
        usm.wait_for_deploy_state = MagicMock(return_value=state_reached)

        show_output = NonCallableMagicMock()
        show_output.get_software_deploy_show_details = MagicMock(
            return_value=[{"State": deploy_state}] if deploy_state else []
        )
        show_object = NonCallableMagicMock()
        show_object.get_state = MagicMock(return_value=deploy_state)
        show_output.get_software_deploy_show = MagicMock(return_value=show_object)
        deploy_show = NonCallableMagicMock()
        deploy_show.get_software_deploy_show = MagicMock(return_value=show_output)

        entries = []
        for release in releases:
            entry = NonCallableMagicMock()
            entry.get_release = MagicMock(return_value=release)
            entries.append(entry)
        list_output = NonCallableMagicMock()
        list_output.get_software_lists = MagicMock(return_value=entries)
        software_list = NonCallableMagicMock()
        software_list.get_software_list = MagicMock(return_value=list_output)

        system_object = NonCallableMagicMock()
        system_object.get_software_version = MagicMock(return_value=running)
        system_output = NonCallableMagicMock()
        system_output.get_system_show_object = MagicMock(return_value=system_object)
        system_show = NonCallableMagicMock()
        system_show.system_show = MagicMock(return_value=system_output)

        object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
        object.__setattr__(keywords, "usm", usm)
        object.__setattr__(keywords, "deploy_show", deploy_show)
        object.__setattr__(keywords, "software_list", software_list)
        object.__setattr__(keywords, "system_show", system_show)
        return keywords

    def test_no_deploy_in_progress_reads_as_empty_state(self):
        """An empty deploy-show table reads as no state rather than raising."""
        keywords = self._build_keywords(deploy_state="")

        self.assertEqual(keywords.get_current_deploy_state(), "")

    def test_deploy_state_is_read_from_the_show_output(self):
        """A deploy in progress reports its state."""
        keywords = self._build_keywords(deploy_state="deploy-activate-done")

        self.assertEqual(keywords.get_current_deploy_state(), "deploy-activate-done")

    def test_require_deploy_state_returns_when_reached(self):
        """Reaching the expected state returns normally."""
        keywords = self._build_keywords(deploy_state="deploy-start-done", state_reached=True)

        keywords.require_deploy_state("deploy-start-done")

    def test_require_deploy_state_raises_when_not_reached(self):
        """An unreached state raises, so a failed deploy cannot proceed to the next phase."""
        keywords = self._build_keywords(deploy_state="deploy-start-failed", state_reached=False)

        with self.assertRaises(KeywordException) as raised:
            keywords.require_deploy_state("deploy-start-done")

        self.assertIn("deploy-start-done", str(raised.exception))
        self.assertIn("deploy-start-failed", str(raised.exception))

    def test_release_id_resolves_a_short_version(self):
        """A short version resolves to the full release ID USM requires."""
        keywords = self._build_keywords(releases=("starlingx-26.03.0", "starlingx-26.10.0"))

        self.assertEqual(keywords.get_release_id_for_version("26.10"), "starlingx-26.10.0")

    def test_release_id_raises_when_the_load_was_never_uploaded(self):
        """No matching release means the target load is missing, which is named as such."""
        keywords = self._build_keywords(releases=("starlingx-26.03.0",))

        with self.assertRaises(KeywordException) as raised:
            keywords.get_release_id_for_version("26.10")

        self.assertIn("software upload", str(raised.exception))

    def test_release_id_prefers_an_exact_version_segment(self):
        """When a version is a substring of several releases, the exact match wins."""
        keywords = self._build_keywords(releases=("starlingx-26.10.0", "starlingx-26.10"))

        self.assertEqual(keywords.get_release_id_for_version("26.10"), "starlingx-26.10")

    def test_release_id_raises_when_ambiguous(self):
        """Several inexact matches are rejected rather than resolved to the first one."""
        keywords = self._build_keywords(releases=("starlingx-26.10.0", "starlingx-26.10.1"))

        with self.assertRaises(KeywordException) as raised:
            keywords.get_release_id_for_version("26.10")

        self.assertIn("several uploaded releases", str(raised.exception))

    def test_running_release_comes_from_the_host(self):
        """The running release is the host's own software version."""
        keywords = self._build_keywords(running="26.10")

        self.assertEqual(keywords.get_running_release(), "26.10")


if __name__ == "__main__":
    unittest.main()
