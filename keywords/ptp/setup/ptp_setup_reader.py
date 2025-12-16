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
            template_file_location (str): Path in the repo to the Template JSON5 file. e.g. 'resources/ptp/ptp_setup_template.json5'

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

    def filter_and_render_ptp_config(self, template_file_location: str, selected_instances: List[Tuple[str, str, List[str]]], custom_configuration_verification_template: Optional[str] = None, configuration_verification_overrides: Optional[Dict[str, Any]] = None) -> PTPSetup:
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
            custom_configuration_verification_template (Optional[str]):
                Jinja2-formatted string representing a configuration_verification override. If provided,
                it replaces the auto-filtered configuration_verification.
            configuration_verification_overrides (Optional[Dict[str, Any]]):
                A dictionary of specific overrides to apply on the generated or provided configuration_verification.
                Supports nested structure (e.g. overriding grandmaster_settings -> clock_class).

        Returns:
            PTPSetup: A PTPSetup object containing the filtered configuration.

        Example:
            filter_and_render_ptp_config(
                template_file_location="resources/ptp/ptp_setup_template.json5",
                selected_instances=[("ptp4", "controller-1", ["ptp4if1"])],
                configuration_verification_overrides={
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
        ptp_config_dict = PTPSetupKeywords._parse_embedded_json(ptp_config_dict)

        # Optionally render custom configuration_verification
        custom_configuration_verification = None
        if custom_configuration_verification_template:
            rendered_custom_configuration_verification = Template(custom_configuration_verification_template).render(render_context)
            custom_configuration_verification = json5.loads(rendered_custom_configuration_verification)

        filtered_json = {"ptp_configuration": {"ptp_instances": {"ptp4l": []}, "ptp_host_ifs": []}, "verification": []}

        ptp_selection = {}
        all_required_ifaces = set()

        for ptp_name, hostname, iface_list in selected_instances:
            if ptp_name not in ptp_selection:
                ptp_selection[ptp_name] = {}
            ptp_selection[ptp_name][hostname] = iface_list
            all_required_ifaces.update(iface_list)

        # Filter ptp_instances.ptp4l
        ptp_config = ptp_config_dict.get("ptp_configuration", {})
        for instance in ptp_config.get("ptp_instances", {}).get("ptp4l", []):
            name = instance.get("name")
            if name in ptp_selection:
                hosts = ptp_selection[name]
                selected_ifaces = [iface for iface_list in hosts.values() for iface in iface_list]
                filtered_json["ptp_configuration"]["ptp_instances"]["ptp4l"].append(
                    {
                        "name": name,
                        "instance_hostnames": list(hosts.keys()),
                        "instance_parameters": instance.get("instance_parameters", ""),
                        "ptp_interface_names": selected_ifaces,
                    }
                )

        # Filter ptp_host_ifs
        for iface in ptp_config.get("ptp_host_ifs", []):
            if iface.get("name") in all_required_ifaces:
                filtered_json["ptp_configuration"]["ptp_host_ifs"].append(iface)

        # Use custom configuration_verification if provided
        if custom_configuration_verification:
            filtered_json["verification"] = [{"type": "pmc", "pmc_values": custom_configuration_verification.get("pmc_values", [])}]
            return PTPSetup(filtered_json)

        # Auto-generate verification by filtering
        verification_data = ptp_config_dict.get("verification", [])
        pmc_values = []
        for ver_item in verification_data:
            if ver_item.get("type") in ["pmc", "pmc_value"]:
                pmc_values = ver_item.get("pmc_values", [])
                break

        filtered_pmc_values = []
        for expected_instance in pmc_values:
            name = expected_instance.get("name")
            if name not in ptp_selection:
                continue

            filtered_instance = {"name": name}

            for hostname, selected_iface_names in ptp_selection[name].items():
                instance_data = expected_instance.get(hostname)
                if not instance_data:
                    continue

                filtered_host_data = {}
                for key in ["parent_data_set", "time_properties_data_set", "grandmaster_settings"]:
                    if key in instance_data:
                        filtered_host_data[key] = instance_data[key]

                # Filter port_data_set based on selected interfaces
                if "port_data_set" in instance_data:
                    if selected_iface_names:
                        # Get actual interface names for selected ptp_interface_names
                        selected_actual_interfaces = set()
                        for iface_name in selected_iface_names:
                            for ptp_host_if in ptp_config.get("ptp_host_ifs", []):
                                if ptp_host_if.get("name") == iface_name:
                                    hostname_key = f"{hostname.replace('-', '_')}_interfaces"
                                    if hostname_key in ptp_host_if:
                                        selected_actual_interfaces.update(ptp_host_if[hostname_key])

                        # Filter port_data_set to only include selected interfaces
                        filtered_port_data_set = []
                        for port in instance_data["port_data_set"]:
                            if "interface" in port and port["interface"] in selected_actual_interfaces:
                                filtered_port_data_set.append(port)

                        if filtered_port_data_set:
                            filtered_host_data["port_data_set"] = filtered_port_data_set
                    else:
                        # If no interfaces specified, include all port_data_set
                        filtered_host_data["port_data_set"] = instance_data["port_data_set"]

                filtered_instance[hostname] = filtered_host_data

            filtered_pmc_values.append(filtered_instance)

        # Apply single-value overrides (like clock_class)
        if configuration_verification_overrides:
            for override in configuration_verification_overrides.get("ptp4l", []):
                override_name = override.get("name")
                for inst in filtered_pmc_values:
                    if inst.get("name") == override_name:
                        for hostname, host_data in override.items():
                            if hostname == "name":
                                continue
                            inst.setdefault(hostname, {})
                            inst[hostname] = self.deep_merge(inst[hostname], host_data)

        filtered_json["verification"] = [{"type": "pmc", "pmc_values": filtered_pmc_values}]
        return PTPSetup(filtered_json)

    @staticmethod
    def _parse_embedded_json(data: Any) -> Any:
        """
        Recursively parse embedded JSON strings in the data structure.

        Args:
            data (Any): The data structure to process.

        Returns:
            Any: The processed data with embedded JSON strings parsed.
        """
        if isinstance(data, dict):
            return {key: PTPSetupKeywords._parse_embedded_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [PTPSetupKeywords._parse_embedded_json(item) for item in data]
        elif isinstance(data, str):
            return json5.loads(data) if data.startswith(("{", "[")) else data
        else:
            return data

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
