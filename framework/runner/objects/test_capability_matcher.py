import pytest

from config.lab.objects.lab_config import LabConfig
from framework.database.objects.testcase import TestCase
from framework.database.operations.lab_capability_operation import LabCapabilityOperation
from framework.database.operations.lab_operation import LabOperation
from framework.database.operations.run_content_operation import RunContentOperation
from framework.pytest_plugins.collection_plugin import CollectionPlugin
from framework.resources.resource_finder import get_stx_repo_root


class TestCapabilityMatcher:
    """
    Class to hold matches for a set of tests given a lab config.
    """

    priority_marker_list = ["p0", "p1", "p2", "p3"]

    def __init__(self, lab_config: LabConfig):
        """
        Constructor

        Args:
            lab_config (LabConfig): Config for the lab
        """
        self.lab_config = lab_config

    def get_list_of_tests(self, test_case_folder: str) -> list[TestCase]:
        """
        Getter for the list of tests that this lab can run.

        Args:
            test_case_folder (str): Path to the folder containing test cases.

        Returns:
            list[TestCase]: List of tests that can be run.
        """
        tests = self._get_all_tests_in_folder(test_case_folder)
        capabilities = self.lab_config.get_lab_capabilities()

        return self._filter_tests(tests, capabilities)

    def get_list_of_tests_from_db(self, run_id: int) -> list[TestCase]:
        """
        This function will return the list of test cases matching the run_id from the database.

        Args:
            run_id (int): Run Id

        Returns:
            list[TestCase]:
        """

        run_content_operation = RunContentOperation()
        tests = run_content_operation.get_tests_from_run_content(run_id)

        lab_operation = LabOperation()
        lab_id = lab_operation.get_lab_id(self.lab_config.get_lab_name())

        lab_capability_operation = LabCapabilityOperation()
        capabilities = list(map(lambda capability: capability.get_capability_marker(), lab_capability_operation.get_lab_capabilities(lab_id)))

        return self._filter_tests(tests, capabilities)

    def _filter_tests(self, tests: list[TestCase], capabilities: list[str]) -> list[TestCase]:
        """
        Filters out the tests that can run on the given lab.

        Args:
            tests (list[TestCase]): The list of tests.
            capabilities (list[str]): The capabilities.

        Returns:
            list[TestCase]: List of tests that can run on the lab based on capabilities.
        """
        tests_to_run = []
        for test in tests:
            markers = self._get_markers(test)
            if not markers or set(markers).issubset(capabilities):
                tests_to_run.append(test)
        return tests_to_run

    def _get_all_tests_in_folder(self, test_case_folder: str) -> list[TestCase]:
        """
        Gets all tests in the testcase folder.

        Args:
            test_case_folder (str): Path to the folder containing test cases.

        Returns:
            list[TestCase]: List of test cases found in the folder.
        """
        repo_root = get_stx_repo_root()
        collection_plugin = CollectionPlugin(repo_root)
        pytest.main(["--collect-only", test_case_folder], plugins=[collection_plugin])
        return collection_plugin.get_tests()

    def _get_markers(self, test: TestCase) -> list[str]:
        """
        Gets the markers for the given test.

        Args:
            test (TestCase): The test case to get markers from.

        Returns:
            list[str]: List of markers associated with the test.
        """
        markers = []
        for marker in test.get_markers():
            # we need to skip any priority markers
            if marker not in self.priority_marker_list:
                markers.append(marker)
        return markers
