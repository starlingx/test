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

    def get_run_headless(self) -> bool:
        """
        Getter for run_headless; Set this to false if you want to see UI tests run in a browser.
        """
        return self.run_headless
