from keywords.k8s.deployments.object.kubectl_deployments_object import KubectlDeploymentObject
from keywords.k8s.deployments.object.kubectl_get_deployments_table_parser import KubectlGetDeploymentTableParser

class KubectlGetDeploymentOutput:
    """
    Class for output of the get deployment command
    """

    def __init__(self, kubectl_get_deployment_output: str):
        """
        Constructor

        Args:
            kubectl_get_deployment_output (str): Raw string output from running a "kubectl get deployment" command.
        """
        self.kubectl_deployments: [KubectlDeploymentObject] = []
        parser = KubectlGetDeploymentTableParser(kubectl_get_deployment_output)
        output_values_list = parser.get_output_values_list()

        for deployment_dict in output_values_list:
            if "NAME" not in deployment_dict:
                continue
            deployment = KubectlDeploymentObject(deployment_dict["NAME"])
            if "READY" in deployment_dict:
                deployment.set_ready(deployment_dict["READY"])
            if "UP-TO-DATE" in deployment_dict:
                deployment.set_up_to_date(deployment_dict["UP-TO-DATE"])
            if "AVAILABLE" in deployment_dict:
                deployment.set_available(deployment_dict["AVAILABLE"])
            if "AGE" in deployment_dict:
                deployment.set_age(deployment_dict["AGE"])
            self.kubectl_deployments.append(deployment)

    def get_deployments(self):
        """
        This function will get the list of all deployments available.

        Returns: List of KubectlDeploymentObjects

        """
        return self.kubectl_deployments


    def is_deployment(self, deployment_name: str) -> bool:
        """
        This function will get the deployment with the name specified from this get_deployment_output.

        Args:
            deployment_name (str): The name of the deployment of interest.

        Returns:
            bool:  This function return a bool value.

        """
        for dep in self.kubectl_deployments:
            if dep.get_name() == deployment_name:
                return True
        else:
            return False
