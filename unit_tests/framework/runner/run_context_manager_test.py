from framework.runner.objects.run_context_manager import RunContextManager, RunContextManagerClass


def test_run_context_manager_is_a_singleton():
    """
    Tests that the module level RunContextManager is an instance of RunContextManagerClass.
    """
    assert isinstance(RunContextManager, RunContextManagerClass)


def test_run_context_manager_defaults_to_no_context():
    """
    Tests that a freshly created run context manager holds no values.
    """
    run_context_manager = RunContextManagerClass()

    assert run_context_manager.get_session_id() is None
    assert run_context_manager.get_jenkins_log_location() is None
    assert run_context_manager.get_test_case_result_id() is None


def test_run_context_manager_stores_the_session_id():
    """
    Tests that the session id set on the run context manager is the one returned.
    """
    run_context_manager = RunContextManagerClass()
    run_context_manager.set_session_id("7ec1a4e6-1a3f-4c1a-9d0f-8f2b6c5d4e3a")

    assert run_context_manager.get_session_id() == "7ec1a4e6-1a3f-4c1a-9d0f-8f2b6c5d4e3a"


def test_run_context_manager_stores_the_jenkins_log_location():
    """
    Tests that the jenkins log location set on the run context manager is the one returned.
    """
    run_context_manager = RunContextManagerClass()
    run_context_manager.set_jenkins_log_location("http://jenkins.example.com/job/example/1/")

    assert run_context_manager.get_jenkins_log_location() == "http://jenkins.example.com/job/example/1/"


def test_run_context_manager_stores_the_test_case_result_id():
    """
    Tests that the deprecated test case result id accessors still round-trip a value.
    """
    run_context_manager = RunContextManagerClass()
    run_context_manager.set_test_case_result_id(1234)

    assert run_context_manager.get_test_case_result_id() == 1234
