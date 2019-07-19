#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import logging
from time import gmtime

from utils import exceptions

FORMAT = '[%(asctime)s] %(lineno)-5d%(levelname)-5s %(threadName)-8s %(' \
         'module)s.%(funcName)-8s:: %(message)s'
# TEST_LOG_LEVEL = 21

TC_STEP_SEP = '=' * 22
TC_START_SEP = '+' * 65
TC_END_SEP = '=' * 60

TC_SETUP_STEP_SEP = TC_TEARDOWN_STEP_SEP = '=' * 22
TC_SETUP_START_SEP = TC_TEARDOWN_START_SEP = TC_RESULT_SEP = '-' * 65


class TisLogger(logging.getLoggerClass()):
    def __init__(self, name='', level=logging.NOTSET):
        super().__init__(name, level)

        # os.makedirs(LOG_DIR, exist_ok=True)
        # logging.basicConfig(level=level, format=FORMAT, filename=FILE_NAME,
        # filemode='w')
        # reset test_step number when creating a logger instance
        self.test_step = -1
        self.test_setup_step = -1
        self.test_teardown_step = -1
        self.show_log = self.isEnabledFor(logging.INFO)

    def tc_func_start(self, tc_name, *args):
        if self.show_log:
            separator = '{}\n'.format(TC_START_SEP)
            self._log(logging.DEBUG,
                      '\n{}Test steps started for: {}'.format(separator,
                                                              tc_name), args)
            self.test_step = 0
            self.test_setup_step = -1
            self.test_teardown_step = -1

    def tc_step(self, msg, *args, **kwargs):
        if self.show_log:
            if self.test_step == -1:
                raise exceptions.ImproperUsage(
                    "Please call tc_func_start() first before calling "
                    "tc_step()!")
            self.test_step += 1
            msg = "\n{} Test Step {}: {}".format(TC_STEP_SEP, self.test_step,
                                                 msg)
            self._log(logging.INFO, msg, args, **kwargs)

    def tc_setup_start(self, tc_name, *args):
        if self.show_log:
            msg = ("\n{}\nSetup started for: {}".format(TC_SETUP_START_SEP,
                                                        tc_name))
            self._log(logging.DEBUG, msg, args)
            self.test_setup_step = 0
            self.test_teardown_step = -1
            self.test_step = -1

    def tc_teardown_start(self, tc_name, *args):
        if self.show_log:
            msg = (
                "\n{}\nTeardown started for: {}".format(TC_TEARDOWN_START_SEP,
                                                        tc_name))
            self._log(logging.DEBUG, msg, args)
            self.test_setup_step = -1
            self.test_step = -1
            self.test_teardown_step = 0

    def tc_result(self, msg, tc_name, *args):
        if self.show_log:
            msg = ("\n{}\nTest Result for: {} - {}\n".format(TC_RESULT_SEP,
                                                             tc_name, msg))
            self._log(logging.INFO, msg, args)
            self.test_step = -1

    def fixture_step(self, msg, *args, **kwargs):

        if self.show_log:

            if self.test_setup_step == -1 and self.test_teardown_step == -1:
                # log as tc_step if the setup steps are executed inside a
                # test function
                if self.test_step != -1:
                    self.tc_step(msg=msg)
                    return

                raise exceptions.ImproperUsage(
                    "Please call tc_setup/teardown_start() to initialize "
                    "fixture step")

            elif self.test_setup_step != -1 and self.test_teardown_step != -1:
                raise exceptions.ImproperUsage(
                    "Please reset fixture step to -1")

            elif self.test_setup_step != -1:
                # in test setup
                self.test_setup_step += 1
                fixture_step = self.test_setup_step
                fixture_ = 'Setup'

            else:
                # in test teardown
                self.test_teardown_step += 1
                fixture_step = self.test_teardown_step
                fixture_ = 'Teardown'

            msg = "\n{} {} Step {}: {}".format(TC_SETUP_STEP_SEP, fixture_,
                                               fixture_step, msg)
            self._log(logging.INFO, msg, args, **kwargs)


# register TiS logger
logging.setLoggerClass(TisLogger)
LOG = logging.getLogger('cgcs_log')
__EXISTING_LOGGERS = {'cgcs_log': LOG}


def __get_logger(name=None):
    if (name == 'cgcs_log') or (not name):
        return LOG
    return logging.getLogger(name)


def get_tis_logger(logger_name, log_path=None, timestamp=gmtime, stream=True,
                   log_format=FORMAT):
    # logger for log saved in file
    existing_loggers = get_existing_loggers()
    if logger_name in existing_loggers:
        return existing_loggers[logger_name]

    if not log_path:
        raise ValueError("log_path has to be provided.")

    logger = __get_logger(name=logger_name)
    logging.Formatter.converter = timestamp
    logger_formatter = logging.Formatter(log_format)
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logger_formatter)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(file_handler)

    if stream:
        # logger for stream output
        stream_hdler = logging.StreamHandler()
        stream_hdler.setFormatter(logger_formatter)
        stream_hdler.setLevel(logging.INFO)
        logger.addHandler(stream_hdler)

    add_logger(logger_name, logger=logger)
    return logger


def get_existing_loggers():
    return __EXISTING_LOGGERS


def add_logger(logger_name, logger):
    __EXISTING_LOGGERS[logger_name] = logger
