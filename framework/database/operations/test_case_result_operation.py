from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.test_case_result import TestCaseResult


class TestCaseResultOperation:
    """
    TestCase Result Operation
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def create_test_case_result(self, test_case_result: TestCaseResult) -> int:
        """
        Creates a test case result in the database

        Args:
            test_case_result (TestCaseResult): the test case result

        Returns:
            int: the test case result

        """
        # A standalone run has no session, so the column has to be left NULL rather than
        # given the string 'None', which is not a valid uuid.
        session_id = f"'{test_case_result.get_session_id()}'" if test_case_result.get_session_id() else "NULL"

        # duration is deliberately absent from the column list. Setting
        # start_time and end_time is what populates it.
        # fmt: off
        create_test_case_result = (
            "INSERT INTO test_case_result (test_id, session_id, result, start_time, end_time, log_hostname, log_location, "
            "jenkins_log_location, failure_file_name, failure_function_name, failure_line_number) "
            f"VALUES ({test_case_result.get_test_id()}, {session_id}, '{test_case_result.get_result()}', "
            f"'{test_case_result.get_start_time()}', '{test_case_result.get_end_time()}', "
            f"'{test_case_result.get_log_hostname()}', '{test_case_result.get_log_location()}', "
            f"'{test_case_result.get_jenkins_log_location()}', '{test_case_result.get_failure_file_name()}', "
            f"'{test_case_result.get_failure_function_name()}', '{test_case_result.get_failure_line_number()}') "
            "RETURNING test_case_result_id"
        )

        result = self.database_operation_manager.execute_query(create_test_case_result)
        return result[0][0]

    def update_test_case_result(self, test_case_result: TestCaseResult):
        """
        Updates a test case result in the database

        Args:
            test_case_result (TestCaseResult): the testcase result

        """
        # fmt: off
        create_test_case_result = (
            "UPDATE test_case_result "
            f"SET result='{test_case_result.get_result()}', "
            f"log_hostname='{test_case_result.log_hostname}', "
            f"log_location='{test_case_result.log_location}', "
            f"start_time='{test_case_result.start_time}', "
            f"end_time='{test_case_result.end_time}' "
            f"WHERE test_case_result_id={test_case_result.get_test_case_result_id()}"
        )

        self.database_operation_manager.execute_query(create_test_case_result, expect_results=False)
