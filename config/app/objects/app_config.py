import json5


class AppConfig:
    """
    Class to hold App config
    """

    def __init__(self, config: str):
        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the app config file: {config}")
            raise

        app_dict = json5.load(json_data)
        self.base_application_path = app_dict["base_application_path"]
        self.istio_app_name = app_dict["istio_app_name"]
        self.metric_server_app_name = app_dict["metric_server_app_name"]

    def get_base_application_path(self) -> str:
        """
        Getter for base application path

        Returns:
            str: the base application path

        """
        return self.base_application_path

    def get_istio_app_name(self) -> str:
        """
        Getter for istio app name

        Returns:
            str: the istio app name path

        """
        return self.istio_app_name

    def get_metric_server_app_name(self) -> str:
        """
        Getter for metric server app name

        Returns:
            str: the metric server app name

        """
        return self.metric_server_app_name
