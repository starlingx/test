import logging
import os
from time import strftime

from config.configuration_manager import ConfigurationManager
from config.logger.objects.logger_config import LoggerConfig
from framework.logging.log_exception_filter import LogExceptionFilter
from framework.logging.log_non_exception_filter import LogNonExceptionFilter

# Singleton instance of the logger
# This instance should never be accessed directly, but instead get_logger() should be used.
_LOGGER = None


class AutomationLogger(logging.getLoggerClass()):
    """
    The logging class defines the operations available to the AutomationLogger.
    """

    GENERAL_LOGGER_FORMAT = "[%(asctime)s] %(source)-3s %(levelname)-7s " "%(threadName)-8s %(module)s.%(funcName)-1s %(lineno)-1d :: %(message)s"
    EXCEPTION_LOGGER_FORMAT = "%(message)s"

    def __init__(self, name: str = "", level: int = logging.INFO):
        """Initialize the AutomationLogger."""
        super().__init__(name, level)
        self.log_folder = None
        self.test_case_log_dir = None
        self._step_counter = 0  # for use in test case step

    def log(self, level: int, message: str, *args, **kwargs) -> None:
        """
        An override of the base logging function. This should only be used by external libraries and no automation code explicitly.

        Args:
            level (int): The LogLevel to be used.
            message (str): The message that will be logged.
            *args: Additional positional arguments for the logger.
            **kwargs: Additional keyword arguments for the logger.
        """
        self._log(level, message, None, stacklevel=2, extra={"source": "LIB"})

    def log_debug(self, message: str) -> None:
        """
        The logging function to use to log debugging information for the user.

        Args:
            message (str): The message that will be logged.
        """
        self._log(logging.DEBUG, message, None, stacklevel=2, extra={"source": "AUT"})

    def log_info(self, message: str) -> None:
        """
        The default logging function to use to log a informative message to the user.

        Args:
            message (str): The message that will be logged.
        """
        self._log(logging.INFO, message, None, stacklevel=2, extra={"source": "AUT"})

    def log_warning(self, message: str) -> None:
        """
        Logs a warning message, indicating a potential issue that is not critical but requires attention.

        Args:
            message (str): The warning message to be logged.
        """
        self._log(logging.WARNING, message, None, stacklevel=2, extra={"source": "AUT"})

    def log_error(self, message: str) -> None:
        """
        The function to call when logging an automation or a software error or exception.

        Args:
            message (str): The message that will be logged.
        """
        self._log(logging.ERROR, message, None, stacklevel=2, extra={"source": "AUT"})

    def log_exception(self, message: str) -> None:
        """
        The function to call only by the framework when logging exceptions and stacktraces.

        Args:
            message (str): The message that will be logged.
        """
        self._log(logging.ERROR, message, None, extra={"source": "EXC"})

    def log_keyword(self, message: str) -> None:
        """
        This debug-level log statement is meant to automatically log all the function calls made. It shouldn't be called explicitly in keywords and test cases.

        Args:
            message (str): The message that will be logged.
        """
        # Setting stacklevel=4 to avoid the find the last stack element before the keyword wrappers
        self._log(logging.DEBUG, message, None, stacklevel=4, extra={"source": "KEY"})

    def log_ssh(self, message: str) -> None:
        """
        This info-level log statement logs everything that is sent and observed from the software under test through an SSH connection.

        Args:
            message (str): The message that will be logged.
        """
        self._log(logging.INFO, message, None, stacklevel=2, extra={"source": "SSH"})

    def log_kpi(self, message: str) -> None:
        """
        This info-level log statement is used to log elapsed time for KPIs.

        Args:
            message (str): The message that will be logged.
        """
        self._log(logging.INFO, message, None, stacklevel=2, extra={"source": "KPI"})

    def get_log_folder(self) -> str:
        """
        Getter for log folder.

        Returns:
            str: The log folder path.
        """
        return self.log_folder

    def get_test_case_log_dir(self) -> str:
        """
        Returns the directory containing the test case logs.

        Returns:
            str: The test case log directory.
        """
        return self.test_case_log_dir

    def reset_step_counter(self) -> None:
        """Reset the test step counter at the beginning of each test case."""
        self._step_counter = 0

    def log_test_case_step(self, description: str, numbered: bool = True) -> None:
        """
        Log a test step with optional automatic numbering and a distinct 'TST' source.

        Args:
            description (str): A short description of the test step.
            numbered (bool): Whether to auto-increment and include the step number.
        """
        if numbered:
            self._step_counter += 1
            message = f"Test Step {self._step_counter}: {description}"
        else:
            message = f"Test Step: {description}"
        self._log(logging.INFO, message, None, stacklevel=2, extra={"source": "TST"})


@staticmethod
def configure_logger() -> None:
    """
    Creates and configures a new logger instance that will be used by the singleton.

    This function must be called before we start using the logger.
    """
    logger_config = ConfigurationManager.get_logger_config()
    lab_configuration = ConfigurationManager.get_lab_config()

    if not logger_config:
        raise ValueError("You must define a Logger Configuration before using the logger.")

    logging.setLoggerClass(AutomationLogger)
    global _LOGGER
    _LOGGER = logging.getLogger("automation_log")

    _LOGGER.log_folder = logger_config.get_log_location()
    if logger_config.get_append_lab_and_timestamp():
        _LOGGER.log_folder = os.path.join(_LOGGER.log_folder, lab_configuration.get_lab_name(), strftime("%Y%m%d%H%M"))
    os.makedirs(_LOGGER.log_folder, exist_ok=True)

    log_file = os.path.join(_LOGGER.get_log_folder(), "full_logs.txt")
    _configure_general_log_handlers(logger_config, log_file)
    _configure_exception_log_handlers(logger_config, log_file)
    _LOGGER.log_info(f"LOG File Location: {log_file}")


@staticmethod
def _configure_general_log_handlers(logger_config: LoggerConfig, log_file: str) -> None:
    """
    This function will add the console and file handlers for general logging.

    Args:
        logger_config (LoggerConfig): LoggerConfig object.
        log_file (str): Full path where we want to store the logs.
    """
    log_formatter = logging.Formatter(_LOGGER.GENERAL_LOGGER_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_formatter)
    file_handler.addFilter(LogNonExceptionFilter())
    file_handler.setLevel(logger_config.get_file_log_level_value())
    _LOGGER.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.addFilter(LogNonExceptionFilter())
    console_handler.setLevel(logger_config.get_console_log_level_value())
    _LOGGER.addHandler(console_handler)


def configure_testcase_log_handler(logger_config: LoggerConfig, log_file: str) -> None:
    """
    Configure the log for the testcase.

    Args:
        logger_config (LoggerConfig): The logger config.
        log_file (str): The log file name.
    """
    log_formatter = logging.Formatter(_LOGGER.GENERAL_LOGGER_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    _LOGGER.test_case_log_dir = os.path.join(_LOGGER.get_log_folder(), f"{log_file}")
    os.makedirs(_LOGGER.test_case_log_dir, exist_ok=True)
    full_log_file_path = os.path.join(_LOGGER.test_case_log_dir, "log.txt")

    file_handler = logging.FileHandler(full_log_file_path)
    file_handler.setFormatter(log_formatter)
    file_handler.addFilter(LogNonExceptionFilter())
    file_handler.setLevel(logger_config.get_file_log_level_value())
    _LOGGER.addHandler(file_handler)

    exception_formatter = logging.Formatter(_LOGGER.EXCEPTION_LOGGER_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")
    exception_file_handler = logging.FileHandler(full_log_file_path)
    exception_file_handler.setFormatter(exception_formatter)
    exception_file_handler.addFilter(LogExceptionFilter())
    exception_file_handler.setLevel(logger_config.get_file_log_level_value())
    _LOGGER.addHandler(exception_file_handler)


def remove_testcase_handler(test_name: str) -> None:
    """
    Remove the testcase handler for the given test.

    Args:
        test_name (str): The test name whose log handler should be removed.
    """
    for handler in _LOGGER.handlers:
        if hasattr(handler, "baseFilename") and f"{test_name}" in handler.baseFilename:
            _LOGGER.removeHandler(handler)


@staticmethod
def _configure_exception_log_handlers(logger_config: LoggerConfig, log_file: str) -> None:
    """
    This function will add the console and file handlers for Exception and stack trace logging.

    Args:
        logger_config (LoggerConfig): LoggerConfig object.
        log_file (str): Full path where we want to store the logs.
    """
    exception_formatter = logging.Formatter("%(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    exception_file_handler = logging.FileHandler(log_file)
    exception_file_handler.setFormatter(exception_formatter)
    exception_file_handler.addFilter(LogExceptionFilter())
    exception_file_handler.setLevel(logger_config.get_file_log_level_value())
    _LOGGER.addHandler(exception_file_handler)

    exception_console_handler = logging.StreamHandler()
    exception_console_handler.setFormatter(exception_formatter)
    exception_console_handler.addFilter(LogExceptionFilter())
    exception_console_handler.setLevel(logger_config.get_console_log_level_value())
    _LOGGER.addHandler(exception_console_handler)


@staticmethod
def get_logger() -> AutomationLogger:
    """
    This function should be used to access the logger.

    Returns:
        AutomationLogger: The singleton instance of the logger if it has been configured.
    """
    global _LOGGER
    if _LOGGER is None:
        configure_logger()
    return _LOGGER
