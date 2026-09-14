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
        self.window_size = web_dict['window_size']

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

    def get_window_size(self) -> str:
        """
        Getter for window_size; the browser window size as "WIDTH,HEIGHT".

        Required for headless runs, where the browser otherwise defaults to an
        800x600 viewport and renders responsive layouts differently.

        Returns:
            str: Window size as "WIDTH,HEIGHT" (e.g. "1920,1080").

        """
        return self.window_size
