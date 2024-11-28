from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.run_content import RunContent
from framework.database.objects.testcase import TestCase
from psycopg2.extras import RealDictCursor


class RunContentOperation:
    """
    Class for Test Run Content Operations
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def get_run_content_from_testplan(self, test_plan_id: int, run_id: int):
        """
        Getter for run content
        Args:
            test_plan_id (): test plan id
            run_id (): the run id

        Returns:

        """
        test_plan_content_query = (
            "select * from test_plan "
            "join session_info using (test_plan_id) "
            "join session_info_content using (session_info_id) "
            "join test_info using (test_info_id) "
            f"where test_plan_id={test_plan_id} "
            "and session_info.enabled=true "
            "and session_info_content.enabled=true"
        )

        results = self.database_operation_manager.execute_query(test_plan_content_query, RealDictCursor)

        test_run_contents = []
        for result in results:
            test_run_content = RunContent(run_id, result['session_info_id'], result['test_info_id'])
            test_run_contents.append(test_run_content)

        return test_run_contents

    def get_tests_from_run_content(self, run_id: int):

        capability_test_query = (
            "SELECT test_info_id, session_info_id, capability_marker from run_content "
            "LEFT JOIN capability_test using (test_info_id) "
            "LEFT JOIN test_info using (test_info_id) "
            "JOIN capability using (capability_id) "
        )

        capability_session_query = (
            "SELECT test_info_id, session_info_id, capability_marker from run_content "
            "LEFT JOIN capability_session using (session_info_id) "
            "LEFT JOIN test_info using (test_info_id) "
            "JOIN capability using (capability_id) "
        )

        full_query = (
            "SELECT run_content_id, test_name, test_suite, priority, test_path, pytest_node_id, test_info_id, "
            "full_capabilities.session_info_id, run_content.test_case_group_id, capability_markers "
            "FROM run_content "
            "JOIN (SELECT test_info_id, session_info_id, string_agg(DISTINCT capability_marker, ', ') AS capability_markers "
            f"FROM ({capability_test_query} "
            "UNION ALL "
            f"{capability_session_query}) as combined_capability "
            "GROUP BY test_info_id, session_info_id) as full_capabilities "
            "USING (test_info_id, session_info_id) "
            "LEFT JOIN test_info using (test_info_id) "
            f"WHERE run_id={run_id}"
        )

        results = self.database_operation_manager.execute_query(full_query, RealDictCursor)

        tests = []
        if results:
            for result in results:
                test = TestCase(result['test_name'], result['test_suite'], result['priority'], result['test_path'], result['pytest_node_id'])
                test.set_test_info_id(result['test_info_id'])
                test.set_test_case_group_id(result['test_case_group_id'])
                test.set_run_content_id(result['run_content_id'])
                if result['capability_markers']:
                    test.set_markers(result['capability_markers'].split(','))
                tests.append(test)

        return tests

    def create_run_content(self, test_plan_id: int, run_id: int):
        """
        Creates run content
        Args:
            test_plan_id (): the test plan id
            run_id (): the run id

        Returns:

        """
        values = []
        run_contents = self.get_run_content_from_testplan(test_plan_id, run_id)
        for run_content in run_contents:
            values.append(
                (
                    run_content.get_run_id(),
                    run_content.get_session_info_id(),
                    run_content.get_test_info_id(),
                    run_content.get_run_content_execution_status(),
                    run_content.get_execution_fail_count(),
                    run_content.get_test_case_group_id(),
                )
            )
        query = "INSERT INTO run_content (run_id, session_info_id, test_info_id, " "run_content_execution_status, execution_fail_count, test_case_group_id) values %s"

        self.database_operation_manager.execute_values(query, values)

    def update_execution_status(self, run_content_id: int, execution_result: str):
        """
        Update Execution result
        Args:
            run_content_id (): the run content id
            execution_result (): execution result

        Returns:

        """
        update_execution_status_query = "UPDATE run_content " f"SET run_content_execution_status='{execution_result}' " f"WHERE run_content_id={run_content_id}"

        self.database_operation_manager.execute_query(update_execution_status_query, expect_results=False)
