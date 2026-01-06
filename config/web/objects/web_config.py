import json5


class WebConfig:
    """
    Class to hold configuration of the WebConfig
    """

    def __init__(self, config):

        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the Web config file: {config}")
            raise

        web_dict = json5.load(json_data)
        self.run_headless = web_dict['run_headless']
        self.start_maximized = web_dict['start-maximized']

    def get_run_headless(self) -> bool:
        """
        Getter for run_headless; Set this to false if you want to see UI tests run in a browser.
        """
        return self.run_headless

    def get_start_maximized(self) -> bool:
        """
        Getter for start_maximized; Set this to true if you want the browser to be maximized.

        Returns:
            bool: True if we are running maximized.

        """
        return self.start_maximized

