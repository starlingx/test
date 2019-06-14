#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import threading
import time
import traceback

from consts.proj_vars import ProjVar
from utils.clients.ssh import SSHClient, ControllerClient, NATBoxClient
from utils.exceptions import ThreadingError
from utils.tis_log import LOG

TIMEOUT_ERR = "Thread did not terminate within timeout. " \
              "Thread details: {} {} {}"
EVENT_TIMEOUT = "Event did not occur within timeout."
INFINITE_WAIT_EVENT_EXPECTED = "There is only one thread (Main Thread), " \
                               "waiting is likely to wait indefinitely"


class MThread(threading.Thread):
    """
    Multi threading class. Allows multiple threads to be run simultaneously.
    e.g. nova_helper.create_flavor('threading', 'auto', vcpus=2, ram=1024) is
    equivalent to...
        thread_1 = MThread(nova_helper.create_flavor, 'threading', 'auto',
        vcpus=2, ram=1024)
        thread_1.start_thread()
        thread_1.wait_for_thread_end()

    Other commands can be run between start_thread and wait_for_thread_end
    The function's output can be retrieved from thread_1.get_output()
    name should NOT be changed
    """
    total_threads = 0
    running_threads = []

    def __init__(self, func, *args, **kwargs):
        """

        Args:
            func (runnable): name of function to run. e.g.
            nova-helper.create_flavor. NOT nova_helper.create_flavor()
            *args:
            **kwargs:
        """
        threading.Thread.__init__(self)
        MThread.total_threads += 1
        self.thread_id = MThread.total_threads
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._output = None
        self._output_returned = threading.Event()
        self.timeout = None
        self._err = None

    def get_output(self, wait=True, timeout=None):
        """
        Get return value of self.func

        Args:
            wait (bool): Whether or not to wait for the output from self.func
            timeout:

        Returns: return value from self.func

        """
        if wait:
            if timeout is None:
                timeout = self.timeout

            if timeout:
                end_time = time.time() + timeout
                while time.time() < end_time:
                    if self._err:
                        raise ThreadingError(str(self._err))
                    if self._output_returned.is_set():
                        # LOG.info("{}: {} returned: {}".format(self.name,
                        # self.func.__name__, self._output.__str__))
                        break

        return self._output

    def get_error_info(self):
        return self._err

    def start_thread(self, timeout=3600):
        """
        Starts a thread.
        Test must wait for thread to terminate or it can continue running
        during other tests.

        Args:
            timeout (int): how long to wait for the thread to finish

        Returns:

        """
        self.timeout = timeout
        self.__start_thread_base()

    def __start_thread_base(self):
        self.start()

    def run(self):
        """
        Do not run this command. Start threads from start_thread functions
        Returns:

        """
        LOG.info("Starting {}".format(self.name))
        # run the function
        try:
            MThread.running_threads.append(self)
            LOG.info("Connecting to lab fip in new thread...")
            lab = ProjVar.get_var('lab')
            lab_fip = lab['floating ip']
            con_ssh = SSHClient(lab_fip)
            con_ssh.connect(use_current=False)
            ControllerClient.set_active_controller(con_ssh)

            if ProjVar.get_var('IS_DC'):
                LOG.info("Connecting to subclouds fip in new thread...")
                ControllerClient.set_active_controller(con_ssh, 'RegionOne')
                con_ssh_dict = ControllerClient.get_active_controllers_map()
                for name in con_ssh_dict:
                    if name in lab:
                        subcloud_fip = lab[name]['floating ip']
                        subcloud_ssh = SSHClient(subcloud_fip)
                        try:
                            subcloud_ssh.connect(use_current=False)
                            ControllerClient.set_active_controller(subcloud_ssh,
                                                                   name=name)
                        except:
                            if name == ProjVar.get_var('PRIMARY_SUBCLOUD'):
                                raise
                            LOG.warning('Cannot connect to {}'.format(name))

            LOG.info("Connecting to NatBox in new thread...")
            NATBoxClient.set_natbox_client()

            LOG.info("Execute function {}({}, {})".format(self.func.__name__,
                                                          self.args,
                                                          self.kwargs))
            self._output = self.func(*self.args, **self.kwargs)
            LOG.info("{} returned: {}".format(self.func.__name__,
                                              self._output.__str__()))
            self._output_returned.set()
        except:
            err = traceback.format_exc()
            # LOG.error("Error found in thread call {}".format(err))
            self._err = err
            raise
        finally:
            LOG.info("Terminating thread: {}".format(self.thread_id))
            if ProjVar.get_var('IS_DC'):
                ssh_clients = ControllerClient.get_active_controllers(
                    current_thread_only=True)
                for con_ssh in ssh_clients:
                    con_ssh.close()
            else:
                ControllerClient.get_active_controller().close()

            natbox_ssh = NATBoxClient.get_natbox_client()
            if natbox_ssh:
                natbox_ssh.close()

            LOG.debug("{} has finished".format(self.name))
            MThread.running_threads.remove(self)

    def wait_for_thread_end(self, timeout=3600, fail_ok=False):
        """
        Waits for thread (self) to finish executing.
        All tests should wait for threads to end before proceeding to
        teardown, unless it is expected to continue,
        e.g. LOG.tc_step will not work during setup or teardown
        Raise error if thread is still running after timeout
        Args:
            timeout (int): how long to wait for the thread to finish.
            self.timeout is preferred.
            fail_ok (bool): fail_ok=False will raise error if wait times out
            or fails test if thread exited due to error

        Returns (bool): True if thread is not running, False/exception otherwise

        """
        if not self.is_alive():
            LOG.info("{} was already finished".format(self.name))
            if self._err:
                if not fail_ok:
                    raise ThreadingError(
                        "Error in thread: {}".format(self._err))
                LOG.error("Error found in thread call {}".format(self._err))
            return True, self._err

        if not timeout:
            timeout = self.timeout

        LOG.info("Wait for {} to finish".format(self.name))
        self.join(timeout)

        if not fail_ok:
            assert not self._err, "{} ran into an error: {}".format(self.name,
                                                                    self._err)

        if not self.is_alive():
            LOG.info("{} has finished".format(self.name))
        else:
            # Thread didn't finish before timeout
            LOG.error("{} did not finish within timeout".format(self.name))
            if fail_ok:
                return False, self._err
            raise ThreadingError(
                TIMEOUT_ERR.format(self.func, self.args, self.kwargs))

        return True, self._err


def get_multi_threads():
    return MThread.running_threads


def is_multi_thread_active():
    if len(get_multi_threads()) == 0:
        return False
    return True


class Events(threading.Event):
    """
    Blocks thread progress when wait_for_event is called
    (Main Thread)               (Thread-1)
    event = Events()
    event.wait_for_event()
    # waits
                                event.set()
    # continues
    """

    def __init__(self, message="Simple event"):
        threading.Event.__init__(self)
        self.message = message
        self.msg_lock = threading.Lock()

    def set(self):
        """
        Set event flag to true. Allows threads waiting for the event to continue
        """
        threading.Event.set(self)
        LOG.info("Event \"{}\" flag set to True".format(self.message))

    def clear(self):
        threading.Event.clear(self)
        LOG.info("Event \"{}\" flag set to False".format(self.message))

    def wait_for_event(self, timeout=3600, fail_ok=False):
        """
        Waits for this Events object to have its flag set to True
        Args:
            timeout:
            fail_ok:

        Returns (bool): True if event flag set to true, False/exception
        otherwise

        """
        if self.is_set():
            LOG.info("Event \"{}\" has already been set".format(self.message))
            return True
        if not timeout:
            LOG.warning(
                "No timeout was specified. This can lead to waiting "
                "indefinitely")

        if not is_multi_thread_active() and not timeout:
            LOG.error(
                "There are no other running threads that can set this event "
                "to true. "
                "This would wait indefinitely")
            raise ThreadingError(INFINITE_WAIT_EVENT_EXPECTED)

        LOG.info(
            "Waiting for event \"{}\" flag set to true".format(self.message))
        if not threading.Event.wait(self, timeout):
            if fail_ok:
                LOG.error(
                    "Timed out waiting for event \"{}\" flag set to "
                    "True".format(
                        self.message))
                return False
            raise ThreadingError(EVENT_TIMEOUT)

        if self.msg_lock.acquire(False):
            # only one message should appear once event is set
            LOG.info("Threads continuing")
            time.sleep(1)
            self.msg_lock.release()
        return True


class TiSBarrier(threading.Barrier):
    """
    Blocks threads calling wait() until specified number (parties) of threads
    are waiting or timeout expires.
    (Main Thread)               (Thread-1)              (Thread-2)
    barr = TiSBarrier(2)
                                barr.wait()
                                # Thread-1 waits
                                                        barr.wait()
                                # both continue
    """

    def __init__(self, parties, action=None, timeout=180):
        """
        Args:
            parties (int): number of threads to wait for
            action (function): additional function to call when barrier breaks
            timeout (int): max wait time
        """
        if len(get_multi_threads()) + 1 < parties:
            LOG.warning(
                "This barrier will wait for more threads than are currently "
                "running")
        threading.Barrier.__init__(self, parties, action, timeout)

        self.timeout = timeout
        LOG.info("Created a barrier waiting for {} threads".format(parties))

    def wait(self, timeout=None):
        """
        Block thread until barrier breaks
        Exception is raised if timeout expires
        Args:
            timeout (int): max wait time at barrier. Preferred over
            self.timeout, if given

        Returns (int): number from 0 to (parties - 1), randomly assigned and
        unique for each thread that waited.
                       -1 if thread did not wait

        """
        self.barrier_status()
        if self.broken:
            return -1
        if not timeout:
            if not self.timeout:
                LOG.warning("This thread does not have a timeout for wait()")
            else:
                timeout = self.timeout

        try:
            LOG.info("Start waiting at barrier")
            id_ = threading.Barrier.wait(self, timeout)
            # only one thread will report the barrier being passed
            if id_ == 0:
                self._barrier_passed()
            return id
        except:
            LOG.info("Barrier broke before {} threads were waiting".format(
                self.parties))
            raise

    def barrier_status(self):
        if not self.broken:
            LOG.info(
                '{} threads are waiting... Barrier waiting for {} '
                'threads'.format(
                    self.n_waiting, self.parties))
        else:
            LOG.info("This barrier has already been passed.")

    def _barrier_passed(self):
        LOG.info("Barrier has been passed. {} threads continuing".format(
            self.parties))


class TiSLock:
    """
    RLock class with added logging
    lock can be acquired using 'lock.acquire()' or 'with lock as have_lock'
    lock released using 'lock.release()' or exiting with scope
    Do Not call __enter__ or __exit__ explicitly

    (Main Thread)               (Thread-1)
    lock = TiSLock()
    lock.acquire()
    # edit test.txt
                                lock.acquire()
                                # waits
    lock.release()
                                # continues
    """

    def __init__(self, blocking=True, timeout=180):
        """
        Create a locking object
        Args:
            blocking (bool): wait for lock to be released if it is locked
            during first acquire attempt
            timeout (int): how long to wait for lock to be released. Should
            set to -1 if blocking is false
                           -1 with blocking True will have no timeout
        """
        self._lock = threading.RLock()
        self.blocking = blocking
        self.timeout = timeout if blocking else -1

    def acquire(self, **kwargs):
        if 'blocking' in kwargs:
            self.blocking = kwargs['blocking']
        if 'timeout' in kwargs:
            self.timeout = kwargs['timeout']
        return self.__enter__()

    def release(self):
        return self.__exit__()

    def __enter__(self):
        """
        Make sure that True is returned.
        Threads will continue if timeout is reached even though lock was not
        acquired

        Returns (bool): True if lock was acquired, False otherwise

        """
        blocking_msg = "" if self.blocking else "not "
        timeout_msg = self.timeout if self.timeout >= 0 else "None"
        msg = "Attempting to acquire lock, {}blocking, timeout - {}".format(
            blocking_msg, timeout_msg)
        LOG.debug(msg)
        got_lock = False
        try:
            got_lock = self._lock.acquire(self.blocking, self.timeout)
        finally:
            if got_lock:
                LOG.debug("Acquired lock")
            else:
                LOG.debug("Could not acquire lock")
            return got_lock

    def __exit__(self, *args):
        LOG.debug("Releasing lock")
        try:
            return self._lock.release()
        except RuntimeError:
            LOG.error("Lock did not release, lock was unlocked already")
            raise
        except:
            LOG.error("An unexpected error was caught when unlocking lock")
            raise
