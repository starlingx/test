import time
from typing import Any, Dict, Optional

import redfish
from redfish.rest.v1 import HttpClient

from framework.exceptions.redfish_client_unreachable_exception import RedFishClientUnreachable
from framework.logging.automation_logger import get_logger


class RedFishClient:
    """
    Class for RedFish client
    """

    def __init__(self, bmc_ip: str, username: str, password: str, timeout: int = 120):
        self.bmc_ip = bmc_ip
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client_obj = None

        self.status_code: int = -1

    def _get_connection(self) -> HttpClient:
        """
        Gets the connection, creates one if it doesn't exist

        Returns:
            HttpClient: the connection
        """
        if self.client_obj is None:
            self.client_obj = self._connect()

        return self.client_obj

    def _connect(self) -> HttpClient:
        """
        Create a connection

        Returns:
            HttpClient: the connection
        """
        self.status_code = -1

        end_time = time.time() + self.timeout
        last_exception = None

        while time.time() < end_time:

            try:
                get_logger().log_info(f"Getting a Redfish client to {self.bmc_ip} ....")
                self.client_obj = redfish.redfish_client(base_url=f"https://{self.bmc_ip}", username=self.username, password=self.password, timeout=30)
                self.client_obj.login(auth="session")
                get_logger().log_info(f"Redfish client established for {self.bmc_ip} ....")
                return self.client_obj
            except Exception as e:
                last_exception = e
                get_logger().log_debug(f"Failed to establish a redfish client: {e}\n Retrying ...")
        else:
            err_msg = f"Failed to open a redfish client for server with ip: {self.bmc_ip} " f"and credentials {self.username}/{self.password}: {last_exception}"
            get_logger().log_warning(err_msg)
            raise RedFishClientUnreachable(err_msg)

    def get(self, path: str, args: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None) -> Any:
        """
        Executes the REST API GET request to query resources' data.

        Args:
            path (str): The URI identifying the resource
            args (Optional[Dict[str, Any]]): Any additional arguments for the REST API HTTP method
            headers (Optional[Dict[str, Any]]): Headers to be appended to the REST API GET request

        Returns:
            Any: Response object from the REST API call
        """
        get_logger().log_debug("running RedFish API:\n" f"METHOD: GET\n" f"URL: {self.bmc_ip}{path}\n" f"ARGS: {args}\n" f"HEADERS: {headers}")
        resp = self._get_connection().get(path=path, args=args, headers=headers)

        end_time = time.time() + self.timeout
        while resp.is_processing and time.time() < end_time:
            time.sleep(1)
        status = resp.status
        get_logger().log_debug(f"Response from RedFish API on URL: {self.bmc_ip}{path}\n:" f"Status: {status}\n" f"Data: {resp.dict}")

        self.status_code = resp.status

        return resp

    def post(self, path: str, args: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None) -> Any:
        """
        Executes the REST API POST request to create or use actions on resources.

        Args:
            path (str): The URI identifying the resource
            args (Optional[Dict[str, Any]]): Any additional arguments for the REST API HTTP method
            body (Optional[Dict[str, Any]]): The payload to be appended to the POST request
            headers (Optional[Dict[str, Any]]): Headers to be appended to the REST API POST request

        Returns:
            Any: Response object from the REST API call
        """
        get_logger().log_debug("running RedFish API:\n" f"METHOD: POST\n" f"URL: {self.bmc_ip}{path}\n" f"ARGS: {args}\n" f"BODY: {body}\n" f"HEADERS: {headers}")
        resp = self._get_connection().post(path=path, args=args, body=body, headers=headers)
        get_logger().log_debug(f"Response from RedFish API on URL: {self.bmc_ip}{path}\n:" f"Status: {resp.status}\n")
        return resp

    def patch(self, path: str, args: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None) -> Any:
        """
        Executes the REST API PATCH request to change or add properties on resources.

        Args:
            path (str): The URI identifying the resource
            args (Optional[Dict[str, Any]]): Any additional arguments for the REST API HTTP method
            body (Optional[Dict[str, Any]]): The payload to be appended to the PATCH request
            headers (Optional[Dict[str, Any]]): Headers to be appended to the REST API PATCH request

        Returns:
            Any: Response object from the REST API call
        """
        return self._get_connection().patch(path=path, args=args, body=body, headers=headers)

    def get_status_code(self) -> int:
        """
        Getter for status code

        Returns:
            int: The status code
        """
        return self.status_code
