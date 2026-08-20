from typing import Any

from framework.options.safe_option_parser import SafeOptionParser
from framework.runner.objects.run_context_manager import RunContextManager


class RunContextLoader:
    """
    Reads the context of the current run off the command line and into the RunContextManager.

    Every product has its own conftest, and each of them needs the same run context, so the
    option definitions and the reading of them live here rather than being repeated.
    """

    @staticmethod
    def add_options(safe_parser: SafeOptionParser):
        """
        Adds the run context options to the given parser.

        Args:
            safe_parser (SafeOptionParser): the parser to add the options to.

        """
        safe_parser.add_option("--session_id", action="store", dest="session_id", help="the id of the session that the results belong to")
        safe_parser.add_option("--jenkins_log_location", action="store", dest="jenkins_log_location", help="the URL of the jenkins job that started this run")
        safe_parser.add_option("--repository", action="store", dest="repository", help="the repository that owns the test cases of this run")

    @staticmethod
    def load_from_pytest_session(session: Any):
        """
        Stores the run context given on the command line of this pytest session in the singleton.

        Args:
            session (Any): the pytest session.

        """
        if session.config.getoption("--session_id"):
            RunContextManager.set_session_id(session.config.getoption("--session_id"))

        if session.config.getoption("--jenkins_log_location"):
            RunContextManager.set_jenkins_log_location(session.config.getoption("--jenkins_log_location"))

        if session.config.getoption("--repository"):
            RunContextManager.set_repository(session.config.getoption("--repository"))
