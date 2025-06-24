import json
from keywords.openstack.openstack.stack.object.openstack_stack_heat_default_enum import OpenstackStackHeatDefaultEnum

class OpenstackReplacementDictParser:
    """
    Class for Auxiliary Replacement dictionary for helping with the manage stack
    """

    def __init__(self, config, default_json_name):
        self.config = config
        self.default_json_name = getattr(OpenstackStackHeatDefaultEnum, default_json_name.upper())
        self.default_json = json.loads(self.default_json_name.value)
        self.replacement_dict = {}
        self.keys_to_exclude = OpenstackStackHeatDefaultEnum.KEEP_JSON.value

        self.flatten_dict(self.default_json)

    def flatten_dict(self, d):
        for key, value in d.items():
            if isinstance(value, dict) and key not in self.keys_to_exclude:
                self.flatten_dict(value)
            else:
                if key in self.config:
                    self.replacement_dict[key] = self.config[key]
                else:
                    self.replacement_dict[key] = value

    def get_replacement_dict(self):
        return self.replacement_dict