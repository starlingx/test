import json5
from jinja2 import Template

from config.configuration_manager import ConfigurationManager
from framework.resources.resource_finder import get_stx_resource_path
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

        ptp_default_status_values_file_path = get_stx_resource_path("resources/ptp/ptp_default_status_values.json5")
        with open(ptp_default_status_values_file_path, "r") as ptp_default_status_values_template_file:
            ptp_default_status_values_template = json5.load(ptp_default_status_values_template_file)

        # Build a replacement dictionary from the PTP Config
        ptp_config = ConfigurationManager.get_ptp_config()
        replacement_dictionary = ptp_config.get_all_hosts_dictionary()

        # Update lab_topology dict with ptp_default_status_values
        replacement_dictionary.update(ptp_default_status_values_template)

        # Render the JSON5 file by replacing the tokens.
        template = Template(json5_template)
        rendered_json_string = template.render(replacement_dictionary)
        json_data = json5.loads(rendered_json_string)

        # Turn the JSON Data into a ptp_setup object.
        ptp_setup = PTPSetup(json_data)
        return ptp_setup
