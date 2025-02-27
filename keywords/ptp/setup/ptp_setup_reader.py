import json5
from jinja2 import Template

from config.configuration_manager import ConfigurationManager
from keywords.base_keyword import BaseKeyword
from keywords.ptp.setup.object.ptp_setup import PTPSetup


class PTPSetupKeywords(BaseKeyword):
    """
    This class is responsible for reading ptp_setup files and matching them with the ptp config.
    """

    def generate_ptp_setup_from_template(self, template_file_location: str) -> PTPSetup:
        """
        This function will read the template_file specified and will replace values based on the ptp_config.

        Args:
            template_file_location (str): Path in the repo to the Template JSON5 file. e.g. 'resources/ptp/setup/ptp_setup_template.json5'

        Returns:
            PTPSetup: An object representing the setup.

        """
        # Load the Template JSON5 file.
        with open(template_file_location, "r") as template_file:
            json5_template = template_file.read()

        # Build a replacement dictionary from the PTP Config
        ptp_config = ConfigurationManager.get_ptp_config()
        replacement_dictionary = ptp_config.get_all_hosts_dictionary()

        # Render the JSON5 file by replacing the tokens.
        template = Template(json5_template)
        rendered_json_string = template.render(replacement_dictionary)
        json_data = json5.loads(rendered_json_string)

        # Turn the JSON Data into a ptp_setup object.
        ptp_setup = PTPSetup(json_data)
        return ptp_setup
