import threading


class ThreadNamer:
    """
    This class is responsible for handling how to name Threads. In particular, it is used to
    name nested threads appropriately.
    e.g. OuterThreadName-InnerThreadName
    """

    def __init__(self):
        """
        Constructor - Capture the name of the current thread.
        """
        self.original_thread_name = threading.current_thread().name

    def get_thread_full_name(self, thread_name):
        """
        This method will combine the name of the current thread with the new name.
        The method will return a combined name that maintains nesting.
        Args:
            thread_name (None | str): Is the name which we want to add to the current Thread.
                                      If this is None, keep the original thread name
        Returns:
            (str) The name for the new thread
        """

        # If thread_name is already contained in the name of the original thread,
        # we aren't adding anything by adding it again.
        if not thread_name or thread_name in self.original_thread_name:
            return self.original_thread_name

        if self.original_thread_name == "MainThread" or "ThreadPoolExecutor" in self.original_thread_name:

            # Simply use the name that was provided
            return thread_name

        else:

            # Keep the full name trace for Nested Threads
            return f"{self.original_thread_name}-{thread_name}"
