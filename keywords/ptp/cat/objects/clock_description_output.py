from keywords.ptp.cat.cat_ptp_table_parser import CatPtpTableParser
from keywords.ptp.cat.objects.clock_description_object import ClockDescriptionObject


class ClockDescriptionOutput:
    """
    This class parses the output of Clock description

    Example:
        productDescription      ;;
        revisionData            ;;
        manufacturerIdentity    00:00:00
        userDescription         ;
        timeSource              0xA0

    """

    def __init__(self, clock_description_output: list[str]):
        """
        Create an internal ClockDescriptionObject from the passed parameter.

        Args:
            clock_description_output (list[str]): a list of strings representing the clock description output
        """
        cat_ptp_table_parser = CatPtpTableParser(clock_description_output)
        output_values = cat_ptp_table_parser.get_output_values_dict()
        self.clock_description_object = ClockDescriptionObject()

        if "productDescription" in output_values:
            self.clock_description_object.set_product_description(output_values["productDescription"])

        if "revisionData" in output_values:
            self.clock_description_object.set_revision_data(output_values["revisionData"])

        if "manufacturerIdentity" in output_values:
            self.clock_description_object.set_manufacturer_identity(output_values["manufacturerIdentity"])

        if "userDescription" in output_values:
            self.clock_description_object.set_user_description(output_values["userDescription"])

        if "timeSource" in output_values:
            self.clock_description_object.set_time_source(output_values["timeSource"])

    def get_clock_description_object(self) -> ClockDescriptionObject:
        """
        Getter for ClockDescriptionObject object.

        Returns:
            ClockDescriptionObject: the clock_description_object
        """
        return self.clock_description_object
