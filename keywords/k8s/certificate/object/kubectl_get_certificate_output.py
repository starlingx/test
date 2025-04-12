from starlingx.keywords.k8s.certificate.object.kubectl_cert_object import KubectlCertObject
from starlingx.keywords.k8s.certificate.object.kubectl_get_certificate_table_parser import KubectlGetCertsTableParser


class KubectlGetCertsOutput:
    """
    This class represents the output of the 'kubectl get certificate' command.

    It parses the raw command output and provides access to certificate objects.
    """

    def __init__(self, kubectl_get_certs_output: str):
        """
        Constructor

        Args:
            kubectl_get_certs_output (str): Raw string output from running a "kubectl get certificate" command.

        """
        self.kubectl_certs: [KubectlCertObject] = []
        kubectl_get_certs_table_parser = KubectlGetCertsTableParser(kubectl_get_certs_output)
        output_values_list = kubectl_get_certs_table_parser.get_output_values_list()

        for pod_dict in output_values_list:

            if "NAME" not in pod_dict:
                raise ValueError(f"There is no NAME associated with the pod: {pod_dict}")

            certs = KubectlCertObject(pod_dict["NAME"])

            if "READY" in pod_dict:
                certs.set_ready(pod_dict["READY"])

            if "SECRET" in pod_dict:
                certs.set_secret(pod_dict["SECRET"])

            if "AGE" in pod_dict:
                certs.set_age(pod_dict["AGE"])

            self.kubectl_certs.append(certs)

    def get_cert(self, certs_name: str) -> KubectlCertObject:
        """
        This function will get the pod with the name specified from this get_pods_output.

        Args:
            certs_name (str): The name of the certs.

        Returns:
            KubectlCertObject: The certificate object with the specified name.

        Raises:
            ValueError: If no certificate with the specified name is found.

        """
        for cert in self.kubectl_certs:
            if cert.get_name() == certs_name:
                return cert
        else:
            raise ValueError(f"There is no certs with the name {certs_name}.")
