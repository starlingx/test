import json5


class K8sConfig:
    """
    Class to hold configuration of the Cloud Platform's K8s Cluster
    """

    def __init__(self, config):

        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the k8s config file: {config}")
            raise

        k8s_dict = json5.load(json_data)
        self.kubeconfig = k8s_dict["kubeconfig"]
        self.dashboard_port = k8s_dict["dashboard_port"]

    def get_kubeconfig(self) -> str:
        """
        Getter for the KUBECONFIG environment variable on the lab where we want to run.
        """
        return self.kubeconfig

    def get_dashboard_port(self) -> str:
        """
        Getter for the port on which the K8s dashboard is running.
        """
        return self.dashboard_port
