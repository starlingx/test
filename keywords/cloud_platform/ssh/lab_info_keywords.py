from config.configuration_manager import ConfigurationManager
from keywords.base_keyword import BaseKeyword


class LabInfoKeywords(BaseKeyword):
    """
    Class for lab info keywords
    """

    def get_fully_qualified_name(self) -> str:
        """
        Returns the fully qualified name of the lab from config

        Returns:
            str: the fully qualified name
        """
        lab_name = ConfigurationManager.get_lab_config().get_lab_name()
        domain_name = ConfigurationManager.get_security_config().get_domain_name()
        return f"{lab_name}.{domain_name}"
