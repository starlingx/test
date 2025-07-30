from keywords.ptp.cat.cat_ptp_cgu_parser import CatPtpCguParser
from keywords.ptp.cat.objects.ptp_cgu_component_object import PtpCguComponentObject


class PtpCguComponentOutput:
    """
    Class for PTP CGU Component Output.
    """

    def __init__(self, cat_ptp_cgu_output: str):
        ptp_cgu_parser = CatPtpCguParser(cat_ptp_cgu_output)
        self.cgu_component = ptp_cgu_parser.parse_ptp_cgu_objects()

    def get_cgu_component(self) -> PtpCguComponentObject:
        """
        Gets the cgu component.

        Returns:
            PtpCguComponentObject: The cgu component object containing parsed values.
        """
        return self.cgu_component
