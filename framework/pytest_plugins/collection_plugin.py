import os
from pathlib import Path
from typing import Any

from framework.database.objects.testcase import TestCase


class CollectionPlugin:
    """
    Plugin that allows us to get all tests after running a collect only in pytest.
    """

    PRIORITIES = ["p0", "p1", "p2", "p3"]

    def __init__(self, repo_root: str):
        """
        Constructor.

        Args:
            repo_root (str): The Absolute path to the root of the repo.
        """
        self.repo_root: str = repo_root
        self.tests: [TestCase] = []

    def _get_full_nodeid(self, test: Any) -> str:
        """
        Ensures the nodeid is relative to the repository root.

        Args:
            test (Any): The pytest test item.

        Returns:
            str: Full nodeid relative to repository root.
        """
        # Get the absolute path of the test file
        abs_path = Path(test.path).absolute()
        repo_root_path = Path(self.repo_root)

        # Make it relative to repo root
        rel_path = abs_path.relative_to(repo_root_path).as_posix()

        # Replace the file path portion of nodeid with the repository-relative path
        parts = test.nodeid.split("::")
        return "::".join([rel_path] + parts[1:])

    def pytest_report_collectionfinish(self, items: Any):
        """
        Run after collection is finished.

        Args:
            items (Any): list of Pytest test items.
        """
        for test in items:
            markers = list(map(lambda marker: marker.name, test.own_markers))
            priority = self.get_testcase_priority(markers)
            if priority:
                markers.remove(priority)

            full_node_id = self._get_full_nodeid(test)
            testcase = TestCase(test.name, os.path.basename(test.location[0]), priority, test.location[0], full_node_id)
            testcase.set_markers(markers)
            self.tests.append(testcase)

    def get_tests(self) -> list[TestCase]:
        """
        Returns the tests.

        Returns:
            list[TestCase]: List of test cases collected during pytest collection.
        """
        return self.tests

    def get_testcase_priority(self, markers: Any) -> str:
        """
        Gets the testcase priority from the list of markers.

        Args:
            markers (Any): the pytest markers to find the priority from.

        Returns:
            str: Testcase priority.
        """
        for mark in markers:
            if mark in self.PRIORITIES:
                return mark
