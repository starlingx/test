from typing import Dict


class SMAConnector:
    """
    Class to handle an SMA connector between two NICs.
    """

    def __init__(self, sma_connector_name: str, sma_connector_dict: Dict[str, str]):
        """
        Constructor.

        Args:
            sma_connector_name (str): The name of this sma_connector
            sma_connector_dict (Dict[str, str]): The dictionary read from the JSON config file associated with this SMA Connector.

        """
        self.name = sma_connector_name

        self.validate_sma_connector_dict(sma_connector_dict)
        self.input_nic = sma_connector_dict["input"]["nic"]
        self.input_sma = sma_connector_dict["input"]["sma"]
        self.output_nic = sma_connector_dict["output"]["nic"]
        self.output_sma = sma_connector_dict["output"]["sma"]

    def validate_sma_connector_dict(self, sma_connector_dict: Dict[str, str]) -> None:
        """
        This function validates that sma_connector_dict is formatted appropriately.

        Args:
            sma_connector_dict (Dict[str, str]): The dictionary read from the JSON config file associated with this SMA Connector.

        """
        if "input" not in sma_connector_dict:
            raise Exception(f"The sma_connector {self.name} must have an input")

        if "nic" not in sma_connector_dict["input"]:
            raise Exception(f"The sma_connector {self.name}'s input must have a nic entry.")

        if "sma" not in sma_connector_dict["input"]:
            raise Exception(f"The sma_connector {self.name}'s input must have an sma entry.")

        if "output" not in sma_connector_dict:
            raise Exception(f"The sma_connector {self.name} must have an input")

        if "nic" not in sma_connector_dict["output"]:
            raise Exception(f"The sma_connector {self.name}'s output must have a nic entry.")

        if "sma" not in sma_connector_dict["output"]:
            raise Exception(f"The sma_connector {self.name}'s output must have an sma entry.")

    def __str__(self):
        """
        String representation of this object.

        Returns (str): String representation of this object.

        """
        return self.name

    def to_dictionary(self) -> Dict[str, str]:
        """
        This function will return a dictionary view of the SMA Connector.

        This is mostly used for substitution in JINJA templates.

        Returns:
            Dict[str, str]: Dictionary representation

        """
        dictionary = {
            "name": self.name,
            "input_nic": self.input_nic,
            "input_sma": self.input_sma,
            "output_nic": self.output_nic,
            "output_sma": self.output_sma,
        }
        return dictionary

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

    def get_input_sma(self) -> str:
        """
        Retrieves the name of the input sma

        Returns (str):
            The name of the input sma
        """
        return self.input_sma

    def get_output_nic(self) -> str:
        """
        Retrieves the name of the output nic

        Returns (str):
            The name of the output nic
        """
        return self.output_nic

    def get_output_sma(self) -> str:
        """
        Retrieves the name of the output sma

        Returns (str):
            The name of the output sma
        """
        return self.output_sma
