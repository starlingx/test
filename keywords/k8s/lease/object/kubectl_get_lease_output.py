"""Output class for kubectl get lease command."""

from keywords.k8s.lease.object.kubectl_get_lease_table_parser import KubectlGetLeaseTableParser
from keywords.k8s.lease.object.kubectl_lease_object import KubectlLeaseObject


class KubectlGetLeaseOutput:
    """Class to parse and query Lease list output."""

    def __init__(self, kubectl_get_lease_output: str | list[str]):
        """Initialize Lease output.

        Args:
            kubectl_get_lease_output (str | list[str]): Raw output from kubectl get lease.
        """
        self.leases: list[KubectlLeaseObject] = []
        parser = KubectlGetLeaseTableParser(kubectl_get_lease_output)
        output_values_list = parser.get_output_values_list()

        for lease_dict in output_values_list:
            if "NAME" not in lease_dict:
                continue
            lease = KubectlLeaseObject(lease_dict["NAME"])
            if "HOLDER" in lease_dict:
                lease.set_holder(lease_dict["HOLDER"])
            if "AGE" in lease_dict:
                lease.set_age(lease_dict["AGE"])
            self.leases.append(lease)

    def get_leases(self) -> list[KubectlLeaseObject]:
        """Get all leases.

        Returns:
            list[KubectlLeaseObject]: List of all lease objects.
        """
        return self.leases

    def get_lease_names(self) -> list[str]:
        """Get all lease names.

        Returns:
            list[str]: List of lease names.
        """
        return [lease.get_name() for lease in self.leases]

    def get_lease_holders(self) -> list[str]:
        """Get all lease holders.

        Returns:
            list[str]: List of lease holder identities.
        """
        return [lease.get_holder() for lease in self.leases if lease.get_holder()]
