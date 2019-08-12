"""This module provides common functions to set up and use the logger."""

import logging
import logging.config
import logging.handlers
import os

import yaml


def setup_logging_using_config(name, config_file):
    """Sets up a logger according to the provided configuration file.

    :param name: the name of the logger, most of the times this should be the
        name of the module
    :param config_file: the path to the config file to be used to set up the
        logger
    :return: returns the instance of the logger already configured
    """
    with open(config_file, 'r') as file_manager:
        config = yaml.safe_load(file_manager.read())
    logging.config.dictConfig(config)

    # create the logger object
    logger = logging.getLogger(name)

    return logger


def setup_logging(
        name, level='info', log_file='StarlingX.log', root=False,
        console_log=True):
    """Sets up a logger according to the desired configuration.

    :param name: the name of the logger, most of the times this should be the
        name of the module
    :param level: the logging level defined for the logger.
        Possible values are: notset, debug, info, warn, error, critical.
    :param log_file: the path and name of the log file to be used in the logger
    :param root: if set to True, the root logger is configured and used, which
        implies that it inherits its configuration to all loggers hierarchy,
        use this if you want to see logs from all modules, even external
        libraries. If set to False, the logger configured is the module's
        logger.
    :param console_log: if True, the console handler will be added to the
        logger, which means that the log will also be shown in the screen,
        if False the messages will only be logged to files
    :return: returns the instance of the logger already configured
    """
    # Determine the correct log level
    if level not in ['notset', 'debug', 'info', 'warn', 'error', 'critical']:
        level = 'info'
    level = getattr(logging, level.upper())

    # create the console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # if the path for the log files does not exist, create it
    if len(log_file.rsplit('/', 1)) == 2:
        log_path = log_file.rsplit('/', 1)[0]
        if not os.path.exists(log_path):
            os.makedirs(log_path)

    # Create the file handlers
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # Max file size 10 MB (10 x 1024 x 1024)
        backupCount=10      # Number of rotating files
        )
    file_handler.setLevel(level)
    error_log_file = (
        '{basename}.error.log'
        .format(basename=log_file.replace('.log', ''))
        )
    error_file_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10485760,  # Max file size 10 MB (10 x 1024 x 1024)
        backupCount=10      # Number of rotating files
        )
    error_file_handler.setLevel(logging.ERROR)

    # create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        '%Y-%m-%d %H:%M:%S')

    # add the formatter to handlers
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    error_file_handler.setFormatter(formatter)

    # create the logger object
    if root:
        logger = logging.getLogger()
        logger.name = name
    else:
        logger = logging.getLogger(name)
        # include log messages from Utils/Libraries/Qemu modules (if any)
        logging.getLogger('Utils').setLevel(level)
        logging.getLogger('Utils').addHandler(file_handler)
        logging.getLogger('Utils').addHandler(error_file_handler)
        logging.getLogger('Libraries').setLevel(level)
        logging.getLogger('Libraries').addHandler(file_handler)
        logging.getLogger('Libraries').addHandler(error_file_handler)
        logging.getLogger('Qemu').setLevel(level)
        logging.getLogger('Qemu').addHandler(file_handler)
        logging.getLogger('Qemu').addHandler(error_file_handler)
        # add the console handler only if enabled
        if console_log:
            logging.getLogger('Utils').addHandler(console_handler)
            logging.getLogger('StarlingX').addHandler(console_handler)

    # set logging level
    logger.setLevel(level)

    # if for some reason this setup function is called multiple times
    # (some applications could do that as a side effect, for example Flask
    # applications), then we need to restrict how many handlers are added to
    # the logger. The logger is a singleton, so there can be only one, but
    # it could have multiple handlers. So if already has a handler(s) (from a
    # previous call) then just use that/those one(s) and don't add more
    # handlers.
    if not logger.handlers:
        # add handlers to the requester module logger
        logger.addHandler(file_handler)
        logger.addHandler(error_file_handler)
        # add the console handler only if enabled
        if console_log:
            logger.addHandler(console_handler)

    # initialize the log with a long line so it is easier to identify when
    # one log finishes and another one begins.
    logger.info(
        '--------------------------------------------------------------')

    return logger
