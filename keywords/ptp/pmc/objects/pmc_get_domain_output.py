from framework.exceptions.keyword_exception import KeywordException
from keywords.ptp.pmc.objects.pmc_get_domain_object import PMCGetDomainObject
from keywords.ptp.pmc.pmc_table_parser import PMCTableParser


class PMCGetDomainOutput:
    """
    This class parses the output of commands such as 'pmc GET DOMAIN'

    Example:
        sending: GET DOMAIN
                507c6f.fffe.0b5a4d-0 seq 0 RESPONSE MANAGEMENT DOMAIN
                        domainNumber 24
    """

    def __init__(self, pmc_output: list[str]):
        """
        Constructor.

            Create an internal DOMAIN from the passed parameter.

        Args:
            pmc_output (list[str]): a list of strings representing the output of the pmc command

        """
        pmc_table_parser = PMCTableParser(pmc_output)

        output_values_list = pmc_table_parser.get_output_values_dict()
        if len(output_values_list) > 1:
            raise KeywordException("More then one domain output was found")
        output_values = output_values_list[0]

        self.pmc_get_domain_object = PMCGetDomainObject()

        if "domainNumber" in output_values:
            self.pmc_get_domain_object.set_domain_number(int(output_values["domainNumber"]))

    def get_pmc_get_domain_object(self) -> PMCGetDomainObject:
        """
        Getter for pmc_get_domain_object object.

        Returns:
            PMCGetDomainObject: A PMCGetDomainObject

        """
        return self.pmc_get_domain_object
