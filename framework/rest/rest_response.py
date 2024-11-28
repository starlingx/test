import json
from requests import Response


class RestResponse:
    """
    Class for Rest Response
    """

    def __init__(self, response: Response):
        self.response = response

    def get_status_code(self) -> int:
        """
        Gets the status code from the response

        Returns: status code
        """
        return self.response.status_code
    
    def get_json_content(self):
        """
        Gets the json content from the response      

        Returns: the json content
        """
        return json.loads(self.response.text)
    
    def get_headers(self):
        """
        Gets the headers from the response        

        Returns: the headers
        """
        return self.response.headers