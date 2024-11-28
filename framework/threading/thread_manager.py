import concurrent
import threading
import traceback
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor

from framework.logging.automation_logger import get_logger
from framework.threading.thread_namer import ThreadNamer
from framework.threading.thread_object import ThreadObject


def execute_function_in_named_thread(thread_object, function_to_execute, *args, **kwargs):
    """
    This function will name the thread for logging purposes

    Args:
        thread_object (ThreadObject): The object representing this thread
        function_to_execute (function): The operation that we want to execute in the thread
        *args:    The list of arguments taken by 'function_to_execute'
        **kwargs: The list of kwargs taken by 'function_to_execute'
    Return: function_to_execute's return value
    """
    try:
        threading.current_thread().name = thread_object.name
        return function_to_execute(*args, **kwargs)
    except Exception as e:
        thread_object.exception = traceback.format_exc()
        raise e


class ThreadManager:
    """
    This class represents an object that will manage threads for a set of operations.
       - Instantiate the class.
       - Call start_thread by passing in the set of commands that you want to run in parallel.
       - Call join_all_threads to wait for all the threads to complete executing successfully.
    If an exception is encountered during any thread, it will be propagated up
    when we call join_all_threads.
    """

    def __init__(self, num_threads: int = 50, timeout: int = 3600, log_thread_status: bool = False):
        """
        This object is used to spawn threads to perform operations and join them all together,
        Args:
            num_threads: Maximum number of threads available to use at a given time.
            timeout: Number of seconds to wait for the threads to complete before timing out
            log_thread_status: True if we want to log when threads start and complete.
        """
        self.future_to_thread_object_dict = {}
        self.executor = ThreadPoolExecutor(max_workers=num_threads)
        self.timeout = timeout
        self.log_thread_status = log_thread_status

    def start_thread(self, thread_name, function_to_execute, *args, **kwargs):
        """
        This function spawn a new thread to execute the function_to_execute

        Args:
            thread_name (str): is used to describe this thread for logging purposes
            function_to_execute (function): is the function to Execute
            *args: is the list of arguments to pass to the function_to_execute
            *kwargs is the list of kwargs to pass to the function_to_execute
        Returns:
            An instance of ThreadObject which contains the future promised by the execution of
            this thread.
        """

        # Pick the name of the Thread, taking nesting into account.
        thread_namer = ThreadNamer()
        full_thread_name = thread_namer.get_thread_full_name(thread_name)
        thread_object = ThreadObject(full_thread_name, thread_name)

        # Start running the function_to_execute in a thread
        future = self.executor.submit(execute_function_in_named_thread, thread_object, function_to_execute, *args, **kwargs)

        # Store the information about the running thread in a ThreadObject
        thread_object.future = future
        self.future_to_thread_object_dict[future] = thread_object

    def join_all_threads(self):
        """
        This function will wait for all the threads spawned by this object to complete.
        The function will also raise an exception if any of the threads has encountered an exception.

        Return:
            results: a map (raw_thread_name, function_to_execute's return values)
        """

        exceptions_in_thread = 0
        results = {}

        try:
            # Wait for all the threads to have completed the operation before moving on.
            for future in futures.as_completed(self.future_to_thread_object_dict.keys(), timeout=self.timeout):

                if self.log_thread_status:
                    get_logger().log_info("Thread {} is done!".format(self.future_to_thread_object_dict[future].name))
                raw_thread_name = self.future_to_thread_object_dict[future].raw_thread_name
                results[raw_thread_name] = future.result()

                # Log Exceptions to the Console as they happen.
                if future.exception():
                    exceptions_in_thread += 1
                    self.future_to_thread_object_dict[future].log_exception()

        except concurrent.futures._base.TimeoutError:
            get_logger().log_error("There is at least one thread that timed out!")
            raise TimeoutError("Thread Timeout")

        # Generate a Report of Failures that happened in the Threads if any.
        if exceptions_in_thread:
            for thread_object in self.future_to_thread_object_dict.values():
                if thread_object.exception:
                    thread_object.log_exception()
            raise AssertionError(f"An error was raised in {exceptions_in_thread} threads.")

        # Resume back to single-threaded execution.
        if self.log_thread_status:
            get_logger().log_info("Thread joining Complete!")

        return results

    def get_thread_object(self, raw_thread_name: str):
        """
        Gets the Thread Object associated with the raw_thread_name specified.

        Args:
            raw_thread_name:

        Returns:

        """
        for thread_object in self.future_to_thread_object_dict.values():
            if thread_object.get_raw_thread_name() == raw_thread_name:
                return thread_object

        raise Exception(f"Failed to find a thread with raw_thread_name='{raw_thread_name}'")
