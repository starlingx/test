from typing import List

import pytest

from framework.database.objects.testcase import TestCase
from framework.database.operations.capability_operation import CapabilityOperation
from framework.database.operations.test_capability_operation import TestCapabilityOperation
from framework.database.operations.test_info_operation import TestInfoOperation
from framework.pytest_plugins.collection_plugin import CollectionPlugin


class TestScannerUploader:
    """
    Class for Scanning tests and uploading.
    """

    def __init__(self, test_folders: List[str]):
        self.test_folders = test_folders

    def scan_and_upload_tests(self, repo_root: str):
        """
        Scans the repo and uploads the new tests to the database.

        Args:
            repo_root (str): The full path to the root of the repo.

        """

        test_info_operation = TestInfoOperation()
        scanned_tests = self.scan_for_tests(repo_root)

        # Filter to find only the test cases in the desired folders.
        filtered_test_cases = []
        for test in scanned_tests:
            if any(test.get_pytest_node_id().startswith(test_folder) for test_folder in self.test_folders):
                filtered_test_cases.append(test)

        # Upload/Update the test cases in the database
        for test in filtered_test_cases:

            print(f"Inserting/Updating - {test.get_test_suite()}::{test.get_test_name()}")
            test_info_id = test_info_operation.get_info_test_id(test.get_test_name(), test.get_test_suite())
            if not test_info_id:
                test_info_id = test_info_operation.insert_test(test)
            database_testcase = test_info_operation.get_test_info(test_info_id)

            # check if any fields need updating
            self.update_priority(test, database_testcase)
            self.update_test_path(test, database_testcase)
            self.update_pytest_node_id(test, database_testcase)
            self.update_capability(test, database_testcase.get_test_info_id())

    def scan_for_tests(self, repo_root: str) -> [TestCase]:
        """
        Scan for tests

        Args:
            repo_root (str): The full path to the root of the repo.

        Returns:
            [TestCase]: list of Testcases

        """
        collection_plugin = CollectionPlugin(repo_root)
        pytest.main(["--collect-only"], plugins=[collection_plugin])
        return collection_plugin.get_tests()

    def update_priority(self, test: TestCase, database_testcase: TestCase):
        """
        Checks the current priority of the test, if it's changed, update it

        Args:
            test (TestCase): the Test in the Repo Scan
            database_testcase (TestCase): the Test in the Database

        """
        database_priority = database_testcase.get_priority()
        local_priority = test.get_priority()
        if local_priority and database_priority is not local_priority:
            test_info_operation = TestInfoOperation()
            test_info_operation.update_priority(database_testcase.get_test_info_id(), local_priority)

    def update_test_path(self, test: TestCase, database_testcase: TestCase):
        """
        Checks the current test_path of the test, if it's changed, update it

        Args:
            test (TestCase): the Test in the Repo Scan
            database_testcase (TestCase): the Test in the Database
        """
        database_test_path = database_testcase.get_test_path()
        actual_test_path = test.get_test_path().replace("\\", "/")

        if not database_test_path or database_test_path is not actual_test_path:
            test_info_operation = TestInfoOperation()
            test_info_operation.update_test_path(database_testcase.get_test_info_id(), actual_test_path)

    def update_pytest_node_id(self, test: TestCase, database_testcase: TestCase):
        """
        Checks the current pytest_node_id of the test, if it's changed, update it

        Args:
            test (TestCase): the Test in the Repo Scan
            database_testcase (TestCase): the Test in the Database
        """
        current_pytest_node_id = database_testcase.get_pytest_node_id()
        if not current_pytest_node_id or current_pytest_node_id is not test.get_pytest_node_id():
            test_info_operation = TestInfoOperation()
            test_info_operation.update_pytest_node_id(database_testcase.get_test_info_id(), test.get_pytest_node_id())

    def update_capability(self, test: TestCase, test_info_id: int):
        """
        Updates the test in the db with any capabilities it has

        Args:
            test (TestCase): the test
            test_info_id (int): the id of the test to check.
        """
        capability_operation = CapabilityOperation()
        capability_test_operation = TestCapabilityOperation()

        # get all the capabilities associated with this test
        capabilities = test.get_markers()
        for capability in capabilities:

            capability_object = capability_operation.get_capability_by_marker(capability)

            # If capability does not exist, raise an exception
            if capability_object == -1:
                raise ValueError(f"No capability with name {capability} exists")

            capability_id = capability_object.get_capability_id()

            mapping_id = capability_test_operation.get_id(capability_id, test_info_id)
            # mapping does not exist, add new one
            if mapping_id == -1:
                capability_test_operation.create_new_mapping(capability_id, test_info_id)

        self.check_for_capabilities_to_remove(test_info_id, capabilities)

    def check_for_capabilities_to_remove(self, test_info_id: int, capabilities: [str]):
        """
        Checks for capabilities in the db that no longer exist on the test

        Args:
            test_info_id (int): the test_info_id
            capabilities ([str]): the capabilities on the test
        """

        # next we need to remove capabilities that are in the database but no longer on the test
        capability_test_operation = TestCapabilityOperation()
        db_capabilities = capability_test_operation.get_capabilities_for_test(test_info_id)

        # get just the marker names to match with test capabilities
        db_marker_names = map(lambda db_capability: db_capability.get_capability_marker(), db_capabilities)

        # this will get the capabilities that exist in the db but not on the test itself
        capabilities_to_be_removed = list(set(db_marker_names).difference(capabilities))

        for marker_name in capabilities_to_be_removed:
            # find the correct db_capability
            db_capability = next(filter(lambda x: x.get_capability_marker() == marker_name, db_capabilities))
            capability_test_operation.delete_capability_test(db_capability.get_capability_id(), test_info_id)
