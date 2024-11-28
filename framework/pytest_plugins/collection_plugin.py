import os

from framework.database.objects.testcase import TestCase


class CollectionPlugin:
    """
    Plugin that allows us to get all tests after running a collect only in pytest
    """

    PRIORITIES = ['p0', 'p1', 'p2', 'p3']

    def __init__(self):
        self.tests: [TestCase] = []

    def pytest_report_collectionfinish(self, items):
        """
        Run after collection is finished
        Args:
            items (): list of test items

        Returns:

        """

        for test in items:
            markers = list(map(lambda marker: marker.name, test.own_markers))
            priority = self.get_testcase_priority(markers)
            if priority:
                markers.remove(priority)

            testcase = TestCase(test.name, os.path.basename(test.location[0]), priority, test.location[0], test.nodeid)
            testcase.set_markers(markers)
            self.tests.append(testcase)

    def get_tests(self) -> [TestCase]:
        """
        Returns the tests
        Returns:

        """
        return self.tests

    def get_testcase_priority(self, markers):
        """
        Gets the testcase priority from the list of markers
        Args:
            markers: the markers to find the priority from

        Returns: testcase priority

        """
        for mark in markers:
            if mark in self.PRIORITIES:
                return mark
