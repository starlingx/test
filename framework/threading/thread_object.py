from framework.logging.automation_logger import get_logger


class ThreadObject:
    """
    This Object represents a Thread that is executed by the ThreadManager.
    """

    def __init__(self, name, raw_thread_name):
        """
        Constructor
        Args:
            name
            raw_thread_name
        Returns: None
        """

        self.name = name
        self.raw_thread_name = raw_thread_name
        self.future = None
        self.exception = None  # Full Trace of the exception if any

    def get_raw_thread_name(self):
        """
        Getter for the Raw Thread name of this thread.
        Returns:

        """

        return self.raw_thread_name

    def get_result(self):
        """
        This function will return the Results associated with this ThreadObject
        Returns:

        """
        if not self.future or self.future._state != 'FINISHED':
            raise Exception(f"The Thread must be finished before we try to get its results. RawThreadName: {self.get_raw_thread_name()}")

        return self.future._result

    def log_exception(self):

        get_logger().log_exception(
            "\n{}\n{}\n{}\n{}{}\n".format(
                "*******************************************************",
                "************ Exception in thread: {} *********".format(self.name),
                "*******************************************************",
                self.exception,
                "*******************************************************",
            )
        )
