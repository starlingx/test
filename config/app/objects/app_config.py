import json5


class AppConfig:
    """
    Class to hold App config.
    """

    def __init__(self, config: str):
        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the app config file: {config}")
            raise

        app_dict = json5.load(json_data)
        self.base_application_path = app_dict["base_application_path"]
        self.platform_integ_app_tarball = app_dict["platform_integ_app_tarball"]
        self.metrics_server_app_tarball = app_dict["metrics_server_app_tarball"]
        self.istio_app_name = app_dict["istio_app_name"]
        self.metric_server_app_name = app_dict["metric_server_app_name"]
        self.oidc_app_name = app_dict["oidc_app_name"]
        self.power_metrics_app_name = app_dict["power_metrics_app_name"]
        self.power_manager_app_name = app_dict["power_manager_app_name"]
        self.intel_device_plugins_app_name = app_dict["intel_device_plugins_app_name"]
        self.node_feature_discovery_app_name = app_dict["node_feature_discovery_app_name"]
        self.node_interface_metrics_exporter_app_name = app_dict["node_interface_metrics_exporter_app_name"]
        self.platform_integ_apps_app_name = app_dict["platform_integ_apps_app_name"]
        self.sriov_fec_operator_app_name = app_dict["sriov_fec_operator_app_name"]

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

    def get_oidc_app_name(self) -> str:
        """
        Getter for oidc app name

        Returns:
            str: the oidc app name

        """
        return self.oidc_app_name

    def get_power_metrics_app_name(self) -> str:
        """
        Getter for power metrics app name

        Returns:
            str: the power metrics app name path

        """
        return self.power_metrics_app_name

    def get_power_manager_app_name(self) -> str:
        """
        Getter for power manager app name

        Returns:
            str: the power manager app name

        """
        return self.power_manager_app_name

    def get_intel_device_plugins_app_name(self) -> str:
        """
        Getter for Intel Device Plugin app name

        Returns:
            str: the intel device plugin app name

        """
        return self.intel_device_plugins_app_name

    def get_node_feature_discovery_app_name(self) -> str:
        """
        Getter for node feature discovery app name

        Returns:
            str: the node feature discovery app name

        """
        return self.node_feature_discovery_app_name

    def get_node_interface_metrics_exporter_app_name(self) -> str:
        """
        Getter for node interface metrics exporter app name

        Returns:
            str: the node interface metrics exporter app name

        """
        return self.node_interface_metrics_exporter_app_name

    def get_platform_integ_apps_app_name(self) -> str:
        """
        Getter for platform integ apps app name

        Returns:
            str: the platform integ apps app name path

        """
        return self.platform_integ_apps_app_name

    def get_platform_integ_app_tarball(self) -> str:
        """
        Getter for platform integ app tarball

        Returns:
            str: the platform integ app tarball

        """
        return self.platform_integ_app_tarball

    def get_metrics_server_app_tarball(self) -> str:
        """
        Getter for metrics server app tarball

        Returns:
            str: the metrics server app tarball

        """
        return self.metrics_server_app_tarball

    def get_sriov_fec_operator_app_name(self) -> str:
        """
        Getter for SRIOV FEC operator name

        Returns:
            str: the sriov fec operator app name

        """
        return self.sriov_fec_operator_app_name
