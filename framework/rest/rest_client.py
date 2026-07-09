import requests
from urllib3.exceptions import InsecureRequestWarning

from framework.rest.rest_response import RestResponse


class RestClient:
    """
    Rest client used for making any rest calls
    """

    def __init__(self):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    def get(self, url: str, headers: dict | list | None = None) -> RestResponse:
        """Runs a get request with the given url and headers.

        Args:
            url (str): The URL for the request.
            headers (dict | list | None): Headers for the request. Defaults to None.

        Returns:
            RestResponse: An object representing the response of the GET request.
        """
        response = requests.get(url, headers=headers, verify=False)
        return RestResponse(response)

    def post(self, url: str, data: dict | str | None = None, headers: dict | list | None = None) -> RestResponse:
        """Runs a post request with the given url and headers.

        Args:
            url (str): The URL for the request.
            data (dict | str | None): The data to be sent in the body of the request.
            headers (dict | list | None): The headers to be used for the request.

        Returns:
            RestResponse: An object containing the response from the request.
        """
        response = requests.post(url, headers=headers, data=data, verify=False)
        return RestResponse(response)

    def delete(self, url: str, headers: dict | None = None) -> RestResponse:
        """
        Runs a delete request with the given url and headers.

        Args:
            url (str): The URL for the request.
            headers (dict | None): Headers for the request.

        Returns:
            RestResponse: The response from the DELETE request.
        """
        response = requests.delete(url, headers=headers, verify=False)
        return RestResponse(response)

    def patch(self, url: str, data: dict | str | None = None, headers: dict | None = None) -> RestResponse:
        """
        Runs a patch request with the given url and headers.

        Args:
            url (str): The URL for the request.
            data (dict | str | None): The data to be sent in the body of the request.
            headers (dict | None): Headers for the request.

        Returns:
            RestResponse: The response from the PATCH request.
        """
        response = requests.patch(url, headers=headers, json=data, verify=False)
        return RestResponse(response)

    def put(self, url: str, data: dict | str | None = None, headers: dict | None = None) -> RestResponse:
        """
        Runs a put request with the given url and headers.

        Args:
            url (str): The URL for the request.
            data (dict | str | None): The data to be sent in the body of the request.
            headers (dict | None): Headers for the request.

        Returns:
            RestResponse: The response from the PUT request.
        """
        response = requests.put(url, headers=headers, json=data, verify=False)
        return RestResponse(response)
