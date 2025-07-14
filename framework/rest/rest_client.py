import requests
from urllib3.exceptions import InsecureRequestWarning

from framework.rest.rest_response import RestResponse


class RestClient:
    """
    Rest client used for making any rest calls
    """

    def __init__(self):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    def get(self, url: str, headers: list[dict[str, str]] = None) -> RestResponse:
        """
        Runs a get request with the given url and headers

        Args:
             url (str): The URL for the request.
            headers (list[dict[str, str]], optional): A list of dictionaries containing header key-value pairs. Defaults to None.

        Returns:
            RestResponse: An object representing the response of the GET request.
        """
        response = requests.get(url, headers=headers, verify=False)
        return RestResponse(response)

    def post(self, url: str, data, headers: list[dict[str, str]]) -> RestResponse:
        """
        Runs a post request with the given url and headers

        Args:
            url (str): The URL for the request.
            data: The data to be sent in the body of the request.
            headers (list[dict[str, str]]): The headers to be used for the request.

        Returns:
            RestResponse: An object containing the response from the request.
        """
        response = requests.post(url, headers=headers, data=data, verify=False)
        return RestResponse(response)
