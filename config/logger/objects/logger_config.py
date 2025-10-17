import logging
import os
from typing import List

import json5


class LoggerConfig:
    """
    Class to hold configuration of the logger
    """

    def __init__(self, config):

        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the logger config file: {config}")
            raise

        log_dict = json5.load(json_data)

        # If it is left as "DEFAULT", then "~/AUTOMATION_LOGS" will be used
        self.log_location = log_dict["log_location"]
        if self.log_location == "DEFAULT":
            home_dir = os.path.expanduser("~")
            subfolder = "AUTOMATION_LOGS"
            self.log_location = os.path.join(home_dir, subfolder)

        self.test_case_resources_log_location = None

        # Log level parsing and validation
        log_levels_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
        }
        self.console_log_level = log_dict["console_log_level"]
        if self.console_log_level not in log_levels_map:
            raise ValueError(f"The provided Console Log Level is invalid. " f"Please select a value in {log_levels_map.keys()}.")
        self.console_log_level_value = log_levels_map[self.console_log_level]

        self.file_log_level = log_dict["file_log_level"]
        if self.file_log_level not in log_levels_map:
            raise ValueError(f"The provided File Log Level is invalid. " f"Please select a value in {log_levels_map.keys()}.")
        self.file_log_level_value = log_levels_map[self.file_log_level]

        self.append_lab_and_timestamp = True
        if "append_lab_and_timestamp" in log_dict:
            self.append_lab_and_timestamp = log_dict["append_lab_and_timestamp"]

        self.testcase_log_index = 1
        if "testcase_log_index" in log_dict:
            self.testcase_log_index = log_dict["testcase_log_index"]

    def get_log_location(self) -> str:
        """
        Getter for the folder where we want to store the log files.

        Returns: the path to the folder where we want to store the log files.
        """
        return self.log_location

    def get_test_case_resources_log_location(self) -> str:
        """
        Getter for the folder where we store resource files used by a test case.

        Returns: the path to the folder where we want to store the resource files used by a test case.
        """
        if not self.test_case_resources_log_location:
            self.test_case_resources_log_location = os.path.join(self.get_log_location(), "resources")
            os.makedirs(self.test_case_resources_log_location, exist_ok=True)

        return self.test_case_resources_log_location

    def get_console_log_level(self) -> str:
        """
        Getter for the console log level as a readable String representation.

        Returns: The console log level that is currently set.
        """
        return self.console_log_level

    def get_console_log_level_value(self) -> str:
        """
        Getter for the console log level value which is used to configure the logger.

        Returns: The console log level that is currently set.
        """
        return self.console_log_level_value

    def get_file_log_level(self) -> str:
        """
        Getter for the file log level as a readable String representation.

        Returns: The file log level that is currently set.
        """
        return self.file_log_level

    def get_file_log_level_value(self) -> str:
        """
        Getter for the file log level value which is used to configure the logger.

        Returns: The file log level that is currently set.
        """
        return self.file_log_level_value

    def get_append_lab_and_timestamp(self) -> bool:
        """
        Getter to see if we should append lab name and timestamp folders to the log file location.

        Returns: Boolean indicating if lab name and timestamp should be appended.
        """
        return self.append_lab_and_timestamp

    def get_testcase_log_index(self) -> int:
        """
        Getter for the current test case log index.

        Returns: The current test case log index.
        """
        return self.testcase_log_index

    def increment_testcase_log_index(self) -> None:
        """
        Increment the test case log index.
        """
        self.testcase_log_index += 1

    def to_log_strings(self) -> List[str]:
        """
        This function will return a list of strings that can be logged to show all the logger configs.

        Returns: A List of strings to be sent to the logger.
        """
        log_strings = []
        log_strings.append(f"log_location: {self.get_log_location()}")
        log_strings.append(f"console_log_level: {self.get_console_log_level()}")
        log_strings.append(f"file_log_level: {self.get_file_log_level()}")

        return log_strings
