from psycopg2.extras import RealDictCursor

from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.testcase import TestCase
from framework.logging.automation_logger import get_logger


class TestInfoOperation:
    """This class allows you to perform test_info database operations."""

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def get_info_test_id(self, test_name: str, test_suite: str, repository: str = "ace") -> int:
        """Transforms the test_name passed in into the equivalent test id.

        The method will return None if test id does not exist.

        Args:
            test_name (str): The name of the test.
            test_suite (str): The suite of the test.
            repository (str): The repository that owns the test. A database can hold tests
                of the same name and suite from more than one repository, so this is needed
                to make the lookup unambiguous.

        Returns:
            int: The id associated with the test.
        """
        # Get the test id from the database.
        get_test_id_query = f"SELECT test_info_id FROM test_info where test_name='{test_name}'" f" and test_suite='{test_suite}' and repository='{repository}'"

        result = self.database_operation_manager.execute_query(get_test_id_query, cursor_factory=RealDictCursor)
        if result:
            if len(result) > 1:
                get_logger().log_info(f"WARNING: We have found more than one result matching the Test Name: {test_name}")
            return result[0]["test_info_id"]

        return None

    def get_test_info(self, test_info_id: str) -> TestCase:
        """Gets the TestInfo associated with the test_info_id specified.

        Args:
            test_info_id (str): The id of the TestInfo of interest.

        Returns:
            TestCase: The test case info from the database.
        """
        test_case_info_query = f"select * from test_info where test_info_id={test_info_id}"

        results = self.database_operation_manager.execute_query(test_case_info_query, RealDictCursor)

        if results:
            # This query returns at maximum one result.
            result = results[0]
            test_info = TestCase(result["test_name"], result["test_suite"], result["priority"], result["test_path"], result["pytest_node_id"])

            test_info.set_test_info_id(result["test_info_id"])
            test_info.set_test_case_group_id(result["test_case_group_id"])
            test_info.set_is_active(result["is_active"])
            if result.get("repository"):
                test_info.set_repository(result["repository"])

            return test_info
        else:
            raise ValueError(f"There is no entry for test_info_id={test_info_id}")

    def get_all_active_tests(self) -> list[TestCase]:
        """Gets all the active testcases in the db.

        Returns:
            list[TestCase]: List of active testcases.
        """
        test_case_info_query = "select * from test_info where is_active=true"

        results = self.database_operation_manager.execute_query(test_case_info_query, RealDictCursor)

        test_info_list = []
        if not results:
            raise ValueError("Did not find any tests in the db.")
        for result in results:
            test_info: TestCase = TestCase(result["test_name"], result["test_suite"], result["priority"], result["test_path"], result["pytest_node_id"])

            test_info.set_test_info_id(result["test_info_id"])
            test_info.set_test_case_group_id(result["test_case_group_id"])
            test_info.set_is_active(result["is_active"])

            test_info_list.append(test_info)
        return test_info_list

    def insert_test(self, testcase: TestCase) -> int:
        """Inserts the given testcase.

        The repository is taken from the TestCase object rather than hardcoded,
        so that callers can set it appropriately before insertion.

        Args:
            testcase (TestCase): The testcase to insert.

        Returns:
            int: The test info id.
        """
        insert_query = f"INSERT INTO test_info (test_name, test_suite, priority, test_path," f" pytest_node_id, test_case_group_id, is_active, repository)" f" VALUES('{testcase.get_test_name()}', '{testcase.get_test_suite()}'," f" '{testcase.get_priority()}', '{testcase.get_test_path()}'," f" '{testcase.get_pytest_node_id()}', {testcase.get_test_case_group_id()}," f" {testcase.is_testcase_active()}, '{testcase.get_repository()}') RETURNING test_info_id"

        result = self.database_operation_manager.execute_query(insert_query, cursor_factory=RealDictCursor)

        if result:
            return result[0]["test_info_id"]
        else:
            raise ValueError(f"Unable to insert testcase with name {testcase.get_test_name()}")

    def update_priority(self, test_info_id: int, priority: str):
        """Updates the priority of the test.

        Args:
            test_info_id (int): The test id.
            priority (str): The priority.
        """
        update_priority_query = f"update test_info set priority='{priority}' where test_info_id={test_info_id}"
        self.database_operation_manager.execute_query(update_priority_query, expect_results=False)

    def update_test_path(self, test_info_id: int, test_path: str):
        """Updates the test_path of this test case.

        Args:
            test_info_id (int): The test id.
            test_path (str): The test_path.
        """
        update_test_path_query = f"update test_info set test_path='{test_path}' where test_info_id={test_info_id}"
        self.database_operation_manager.execute_query(update_test_path_query, expect_results=False)

    def update_pytest_node_id(self, test_info_id: int, pytest_node_id: str):
        """Updates the pytest_node_id of this test case.

        Args:
            test_info_id (int): The test_info_id.
            pytest_node_id (str): The pytest_node_id.
        """
        update_pytest_node_id_query = f"update test_info set pytest_node_id='{pytest_node_id}' where test_info_id={test_info_id}"
        self.database_operation_manager.execute_query(update_pytest_node_id_query, expect_results=False)

    def update_repository(self, test_info_id: int, repository: str):
        """Updates the repository of this test case.

        Args:
            test_info_id (int): The test_info_id.
            repository (str): The repository name.
        """
        update_repository_query = f"update test_info set repository='{repository}' where test_info_id={test_info_id}"
        self.database_operation_manager.execute_query(update_repository_query, expect_results=False)

    def set_test_active(self, test_info_id: int):
        """Sets the given test to be active.

        Args:
            test_info_id (int): The test id.
        """
        set_active_query = f"UPDATE test_info SET is_active=true where test_info_id={test_info_id}"
        self.database_operation_manager.execute_query(set_active_query, expect_results=False)

    def set_tests_inactive(self, test_ids: list[int]):
        """Sets the given tests to be inactive.

        Args:
            test_ids (list[int]): The list of test ids.
        """
        list_of_ids = ",".join(map(str, test_ids))
        set_inactive_query = f"UPDATE test_info SET is_active=false where test_info_id in ({list_of_ids})"

        self.database_operation_manager.execute_query(set_inactive_query, expect_results=False)
