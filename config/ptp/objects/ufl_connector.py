from typing import Dict


class UFLConnector:
    """
    Class to handle a UFL connector between two NICs.
    """

    def __init__(self, ufl_connector_name: str, ufl_connector_dict: Dict[str, str]):
        """
        Constructor.

        Args:
            ufl_connector_name (str): The name of this ufl_connector
            ufl_connector_dict (Dict[str, str]): The dictionary read from the JSON config file associated with this UFL Connector.

        """
        self.name = ufl_connector_name

        self.validate_ufl_connector_dict(ufl_connector_dict)
        self.input_nic = ufl_connector_dict["input"]["nic"]
        self.input_ufl = ufl_connector_dict["input"]["ufl"]
        self.output_nic = ufl_connector_dict["output"]["nic"]
        self.output_ufl = ufl_connector_dict["output"]["ufl"]

    def validate_ufl_connector_dict(self, ufl_connector_dict: Dict[str, str]) -> None:
        """
        This function validates that ufl_connector_dict is formatted appropriately.

        Args:
            ufl_connector_dict (Dict[str, str]): The dictionary read from the JSON config file associated with this UFL Connector.

        """
        if "input" not in ufl_connector_dict:
            raise Exception(f"The ufl_connector {self.name} must have an input")

        if "nic" not in ufl_connector_dict["input"]:
            raise Exception(f"The ufl_connector {self.name}'s input must have a nic entry.")

        if "ufl" not in ufl_connector_dict["input"]:
            raise Exception(f"The ufl_connector {self.name}'s input must have a ufl entry.")

        if "output" not in ufl_connector_dict:
            raise Exception(f"The ufl_connector {self.name} must have an input")

        if "nic" not in ufl_connector_dict["output"]:
            raise Exception(f"The ufl_connector {self.name}'s output must have a nic entry.")

        if "ufl" not in ufl_connector_dict["output"]:
            raise Exception(f"The ufl_connector {self.name}'s output must have a ufl entry.")

    def __str__(self):
        """
        String representation of this object.

        Returns (str): String representation of this object.

        """
        return self.name

    def get_name(self) -> str:
        """
        Retrieves the name from the SMA connector.

        Returns (str):
            The name of the SMA connector.
        """
        return self.name

    def get_input_nic(self) -> str:
        """
        Retrieves the name of the input nic

        Returns (str):
            The name of the input nic
        """
        return self.input_nic

    def get_input_ufl(self) -> str:
        """
        Retrieves the name of the input ufl

        Returns (str):
            The name of the input ufl
        """
        return self.input_ufl

    def get_output_nic(self) -> str:
        """
        Retrieves the name of the output nic

        Returns (str):
            The name of the output nic
        """
        return self.output_nic

    def get_output_ufl(self) -> str:
        """
        Retrieves the name of the output ufl

        Returns (str):
            The name of the output ufl
        """
        return self.output_ufl
