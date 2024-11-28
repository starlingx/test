from keywords.k8s.service.object.kubectl_get_service_table_parser import KubectlGetServiceTableParser
from keywords.k8s.service.object.kubectl_service_object import KubectlServiceObject


class KubectlGetServiceOutput:
    """
    Class for output of the get service command
    """

    def __init__(self, kubectl_get_service_output: str):
        """
        Constructor

        Args:
            kubectl_get_service_output: Raw string output from running a "kubectl get service" command.

        """

        self.kubectl_service: [KubectlServiceObject] = []
        kubectl_get_service_table_parser = KubectlGetServiceTableParser(kubectl_get_service_output)
        output_values_list = kubectl_get_service_table_parser.get_output_values_list()

        for service_dict in output_values_list:

            if 'NAME' not in service_dict:
                raise ValueError(f"There is no NAME associated with the service: {service_dict}")

            service = KubectlServiceObject(service_dict['NAME'])

            if 'TYPE' in service_dict:
                service.set_type(service_dict['TYPE'])

            if 'CLUSTER-IP' in service_dict:
                service.set_cluster_ip(service_dict['CLUSTER-IP'])

            if 'EXTERNAL-IP' in service_dict:
                service.set_external_ip(service_dict['EXTERNAL-IP'])

            if 'AGE' in service_dict:
                service.set_age(service_dict['AGE'])

            if 'PORT(S)' in service_dict:
                service.set_ports(service_dict['PORT(S)'])

            self.kubectl_service.append(service)

    def get_service(self, service_name) -> KubectlServiceObject:
        """
        This function will get the service with the name specified from this get_service_output.
        Args:
            service_name: The name of the service of interest.

        Returns: KubectlServiceObject

        """
        for service_name_object in self.kubectl_service:
            if service_name_object.get_name() == service_name:
                return service_name_object
        else:
            raise ValueError(f"There is no service with the name {service_name}.")
