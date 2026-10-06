from typing import Optional


class BiosToolSystemInfo:
    """BMC-reported system Manufacturer/Model.

    Exposes its fields through getters rather than public attributes, to
    follow the repository's convention for strong result objects (e.g.
    :class:`SystemInfo`, :class:`BiosAttribute`).
    """

    def __init__(self, manufacturer: Optional[str], model: Optional[str]):
        """Initialize a BiosToolSystemInfo.

        Args:
            manufacturer (Optional[str]): The BMC-reported manufacturer.
            model (Optional[str]): The BMC-reported model.
        """
        self.manufacturer = manufacturer
        self.model = model

    def get_manufacturer(self) -> Optional[str]:
        """Get the BMC-reported manufacturer.

        Returns:
            Optional[str]: The manufacturer, or None if not reported.
        """
        return self.manufacturer

    def get_model(self) -> Optional[str]:
        """Get the BMC-reported model.

        Returns:
            Optional[str]: The model, or None if not reported.
        """
        return self.model
