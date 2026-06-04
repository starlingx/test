"""Typed object representing one row from ``kubectl get ingress``."""

from typing import Optional


class KubectlIngressObject:
    """
    Represents a single Kubernetes Ingress resource.
    """

    def __init__(self, name: str):
        """
        Constructor.

        Args:
            name (str): The ingress resource name.
        """
        self.name = name
        self.ingress_class: Optional[str] = None
        self.hosts: Optional[str] = None
        self.address: Optional[str] = None
        self.ports: Optional[str] = None
        self.age: Optional[str] = None

    def get_name(self) -> str:
        """
        Getter for NAME entry.

        Returns:
            str: The name of the ingress.
        """
        return self.name

    def set_ingress_class(self, ingress_class: str) -> None:
        """
        Setter for the CLASS column.

        Args:
            ingress_class (str): The ingress class value.
        """
        self.ingress_class = ingress_class

    def get_ingress_class(self) -> Optional[str]:
        """
        Getter for CLASS entry.

        Returns:
            Optional[str]: The ingress class of the ingress.
        """
        return self.ingress_class

    def set_hosts(self, hosts: str) -> None:
        """
        Setter for the HOSTS column.

        Args:
            hosts (str): The hosts value.
        """
        self.hosts = hosts

    def get_hosts(self) -> Optional[str]:
        """
        Getter for HOSTS entry.

        Returns:
            Optional[str]: The hosts configured on the ingress.
        """
        return self.hosts

    def set_address(self, address: str) -> None:
        """
        Setter for the ADDRESS column.

        Args:
            address (str): The address value.
        """
        self.address = address

    def get_address(self) -> Optional[str]:
        """
        Getter for ADDRESS entry.

        Returns:
            Optional[str]: The address advertised by the ingress controller.
        """
        return self.address

    def set_ports(self, ports: str) -> None:
        """
        Setter for the PORTS column.

        Args:
            ports (str): The ports value.
        """
        self.ports = ports

    def get_ports(self) -> Optional[str]:
        """
        Getter for PORTS entry.

        Returns:
            Optional[str]: The ports exposed by the ingress.
        """
        return self.ports

    def set_age(self, age: str) -> None:
        """
        Setter for the AGE column.

        Args:
            age (str): The age value.
        """
        self.age = age

    def get_age(self) -> Optional[str]:
        """
        Getter for AGE entry.

        Returns:
            Optional[str]: The age of the ingress resource.
        """
        return self.age

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"Ingress: {self.name} (class={self.ingress_class}, hosts={self.hosts})"

    def __repr__(self) -> str:
        """Return a debug string representation."""
        return f"<KubectlIngressObject name={self.name} class={self.ingress_class} hosts={self.hosts} address={self.address} ports={self.ports} age={self.age}>"
