import copy
from typing import Any, Dict, List, Optional, Tuple

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

    def filter_and_render_ptp_config(self, template_file_location: str, selected_instances: List[Tuple[str, str, List[str]]], custom_expected_dict_template: Optional[str] = None, expected_dict_overrides: Optional[Dict[str, Any]] = None) -> PTPSetup:
        """
        Filters and renders a PTP configuration from a JSON5 template based on selected instances.

        This function is useful for generating a partial configuration from a complete PTP setup,
        based on specific instance names, hostnames, and interfaces. It also allows:
        - Overriding expected_dict via a custom Jinja2 template string
        - Applying deep overrides to specific values (e.g., changing `clock_class`)

        Args:
            template_file_location (str): Path to the JSON5 template file.
            selected_instances (List[Tuple[str, str, List[str]]]):
                List of tuples, where each tuple contains:
                    - ptp_instance_name (str)
                    - hostname (str)
                    - list of associated interface names (List[str])
            custom_expected_dict_template (Optional[str]):
                Jinja2-formatted string representing an expected_dict override. If provided,
                it replaces the auto-filtered expected_dict.
            expected_dict_overrides (Optional[Dict[str, Any]]):
                A dictionary of specific overrides to apply on the generated or provided expected_dict.
                Supports nested structure (e.g. overriding grandmaster_settings -> clock_class).

        Returns:
            PTPSetup: A PTPSetup object containing the filtered configuration.

        Example:
            filter_and_render_ptp_config(
                template_file_location="resources/ptp/setup/ptp_setup_template.json5",
                selected_instances=[("ptp4", "controller-1", ["ptp4if1"])],
                expected_dict_overrides={
                    "ptp4l": [
                        {
                            "name": "ptp4",
                            "controller-1": {
                                "grandmaster_settings": {
                                    "clock_class": 165
                                }
                            }
                        }
                    ]
                }
            )
        """
        # Load and render the JSON5 template
        with open(template_file_location, "r") as template_file:
            json5_template = template_file.read()

        ptp_defaults_path = get_stx_resource_path("resources/ptp/ptp_default_status_values.json5")
        with open(ptp_defaults_path, "r") as defaults_file:
            ptp_defaults = json5.load(defaults_file)

        ptp_config = ConfigurationManager.get_ptp_config()
        render_context = ptp_config.get_all_hosts_dictionary()
        render_context.update(ptp_defaults)

        # Render main config template
        rendered_config = Template(json5_template).render(render_context)
        ptp_config_dict = json5.loads(rendered_config)

        # Optionally render custom expected_dict
        custom_expected_dict = None
        if custom_expected_dict_template:
            rendered_custom_expected = Template(custom_expected_dict_template).render(render_context)
            custom_expected_dict = json5.loads(rendered_custom_expected)

        filtered_json = {"ptp_instances": {"ptp4l": []}, "ptp_host_ifs": [], "expected_dict": {"ptp4l": []}}

        ptp_selection = {}
        all_required_ifaces = set()

        for ptp_name, hostname, iface_list in selected_instances:
            if ptp_name not in ptp_selection:
                ptp_selection[ptp_name] = {}
            ptp_selection[ptp_name][hostname] = iface_list
            all_required_ifaces.update(iface_list)

        # Filter ptp_instances.ptp4l
        for instance in ptp_config_dict.get("ptp_instances", {}).get("ptp4l", []):
            name = instance.get("name")
            if name in ptp_selection:
                hosts = ptp_selection[name]
                selected_ifaces = [iface for iface_list in hosts.values() for iface in iface_list]
                filtered_json["ptp_instances"]["ptp4l"].append(
                    {
                        "name": name,
                        "instance_hostnames": list(hosts.keys()),
                        "instance_parameters": instance.get("instance_parameters", ""),
                        "ptp_interface_names": selected_ifaces,
                    }
                )

        # Filter ptp_host_ifs
        for iface in ptp_config_dict.get("ptp_host_ifs", []):
            if iface.get("name") in all_required_ifaces:
                filtered_json["ptp_host_ifs"].append(iface)

        # Use custom expected_dict if provided
        if custom_expected_dict:
            filtered_json["expected_dict"]["ptp4l"] = custom_expected_dict.get("ptp4l", [])
            return PTPSetup(filtered_json)

        # Auto-generate expected_dict by filtering
        for expected_instance in ptp_config_dict.get("expected_dict", {}).get("ptp4l", []):
            name = expected_instance.get("name")
            if name not in ptp_selection:
                continue

            filtered_instance = {"name": name}

            for hostname, _ in ptp_selection[name].items():
                instance_data = expected_instance.get(hostname)
                if not instance_data:
                    continue

                filtered_instance[hostname] = {key: instance_data.get(key) for key in ["parent_data_set", "time_properties_data_set", "grandmaster_settings", "port_data_set"]}

            filtered_json["expected_dict"]["ptp4l"].append(filtered_instance)

        # Apply single-value overrides (like clock_class)
        if expected_dict_overrides:
            for override in expected_dict_overrides.get("ptp4l", []):
                override_name = override.get("name")
                for inst in filtered_json["expected_dict"]["ptp4l"]:
                    if inst.get("name") == override_name:
                        for hostname, host_data in override.items():
                            if hostname == "name":
                                continue
                            inst.setdefault(hostname, {})
                            inst[hostname] = self.deep_merge(inst[hostname], host_data)

        return PTPSetup(filtered_json)

    def deep_merge(self, dest: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merges the contents of `src` into `dest`.

        If both `dest` and `src` contain a value for the same key and both values are dictionaries,
        they will be merged recursively. Otherwise, the value from `src` overrides the one in `dest`.

        This is useful for applying nested configuration overrides without losing existing structure.

        Args:
            dest (Dict[str, Any]): The original dictionary to merge into.
            src (Dict[str, Any]): The dictionary containing overriding or additional values.

        Returns:
            Dict[str, Any]: A new dictionary representing the merged result.

        Example:
            deep_merge({"ptp4l": [{"name": "ptp4", "controller-1": {"grandmaster_settings": {"clock_class": 165}}}]}}
        """
        result = copy.deepcopy(dest)
        for key, value in src.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self.deep_merge(result[key], value)
            else:
                result[key] = value
        return result
