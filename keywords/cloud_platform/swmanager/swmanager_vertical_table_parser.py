import yaml


class SwManagerVerticalTableParser:
    """
    Class for SwManager vertical table parsing.

    In a vertical table, attributes and their corresponding values are arranged in
    structured text, with each attribute listed alongside its value.

    As an example of a typical argument for the constructor of this class,
    consider the output of the command 'sw-manager fw-update-strategy show':

    ```
    Strategy Firmware Update Strategy:
      strategy-uuid:                          52bf402f-54ab-4fee-8155-4e0b23bd3463
      controller-apply-type:                  ignore
      storage-apply-type:                     ignore
      worker-apply-type:                      serial
      default-instance-action:                stop-start
      alarm-restrictions:                     strict
      current-phase:                          build
      current-phase-completion:               100%
      state:                                  build-failed
      build-result:                           failed
      build-reason:                           alarms ['100.104'] from platform are present
    ```
    """

    def __init__(self, swmanager_output):
        self.swmanager_output = swmanager_output

    def get_output_values_dict(self) -> dict:
        """Retrieves the output values from `self.swmanager_output` as a dictionary.

        This method parses the YAML content stored in `self.swmanager_output` and returns
        it as a dictionary. Each key-value pair in the resulting dictionary corresponds
        to entries from the parsed YAML data.

        Returns:
            dict: A dictionary representation of the parsed YAML content.
        """
        output_values_dict = yaml.safe_load("".join(self.swmanager_output))
        return output_values_dict
