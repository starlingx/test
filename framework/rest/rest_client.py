import requests
from framework.rest.rest_response import RestResponse
from urllib3.exceptions import InsecureRequestWarning


class RestClient:
    """
    Rest client used for making any rest calls
    """

    def __init__(self):
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    def get(self, url: str, headers: list[dict[str, str]]) -> RestResponse:
        """
        Runs a get request with the given url and headers
        Args:
            url: the url for the request
            headers: the headers to be used for the call

        Returns: RestResponse Object
        """
        response = requests.get(url, headers=headers, verify=False)
        return RestResponse(response)

    def post(self, url: str, data, headers: list[dict[str, str]]):
        """
        Runs a post request with the given url and headers
        Args:
            url: the url for the request
            headers: the headers to be used for the call

        Returns: RestResponse Object
        """
        response = requests.post(url, headers=headers, data=data, verify=False)
        return RestResponse(response)
