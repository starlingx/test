class RunContextManagerClass:
    """
    Singleton class for storing the context of the current run.

    The context is supplied by the caller as pytest command line options. It holds the
    identifiers that the test framework needs in order to associate the results that it
    writes with the run that requested them.
    """

    def __init__(self):
        self.session_id = None
        self.jenkins_log_location = None
        self.repository = "ace"
        self.test_case_result_id = None

    def get_session_id(self) -> str:
        """
        Getter for the session id.

        Returns:
            str: the session id of the run, None if the run wasn't given one.

        """
        return self.session_id

    def set_session_id(self, session_id: str):
        """
        Setter for the session id.

        Args:
            session_id (str): the session id of the run.

        """
        self.session_id = session_id

    def get_jenkins_log_location(self) -> str:
        """
        Getter for the jenkins log location.

        Returns:
            str: the URL of the jenkins job that started the run, None if there isn't one.

        """
        return self.jenkins_log_location

    def set_jenkins_log_location(self, jenkins_log_location: str):
        """
        Setter for the jenkins log location.

        Args:
            jenkins_log_location (str): the URL of the jenkins job that started the run.

        """
        self.jenkins_log_location = jenkins_log_location

    def get_repository(self) -> str:
        """
        Getter for the repository.

        A database can hold test cases of the same name and suite that belong to more than one
        repository, so the repository is needed to look a test case up. Test cases in this
        framework belong to more than one repository, and the caller of the run is the one that
        knows which, so it tells us.

        Returns:
            str: the repository that owns the test cases of this run, 'ace' by default.

        """
        return self.repository

    def set_repository(self, repository: str):
        """
        Setter for the repository.

        Args:
            repository (str): the repository that owns the test cases of this run.

        """
        self.repository = repository

    def get_test_case_result_id(self) -> int:
        """
        Getter for the test case result id.

        Deprecated:
            Results are now inserted when the test case ends, so the caller no longer
            pre-creates a result row. This accessor is retained only so that a caller
            passing the old option is not rejected. It will be removed.

        Returns:
            int: the test case result id, None if the run wasn't given one.

        """
        return self.test_case_result_id

    def set_test_case_result_id(self, test_case_result_id: int):
        """
        Setter for the test case result id.

        Deprecated:
            Results are now inserted when the test case ends, so the caller no longer
            pre-creates a result row. This accessor is retained only so that a caller
            passing the old option is not rejected. It will be removed.

        Args:
            test_case_result_id (int): the test case result id.

        """
        self.test_case_result_id = test_case_result_id


RunContextManager = RunContextManagerClass()
