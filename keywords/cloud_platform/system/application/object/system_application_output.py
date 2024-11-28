from keywords.cloud_platform.system.application.object.system_application_object import SystemApplicationObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemApplicationOutput:
    """
    This class parses the output of commands such as 'system application-upload', 'system application-apply', and others
    that share the same output as shown in the example below.
    The parsing result is a 'SystemApplicationObject' instance.

    Example:
        'system application-upload -n hello-kitty-min-k8s-version.tgz -v 0.1.0 hello-kitty-min-k8s-version.tgz'
        +---------------+----------------------------------+
        | Property      | Value                            |
        +---------------+----------------------------------+
        | active        | False                            |
        | app_version   | 0.1.0                            |
        | created_at    | 2024-10-14T18:11:52.261952+00:00 |
        | manifest_file | fluxcd-manifests                 |
        | manifest_name | hello-kitty-fluxcd-manifests     |
        | name          | hello-kitty                      |
        | progress      | None                             |
        | status        | uploading                        |
        | updated_at    | None                             |
        +---------------+----------------------------------+

    """

    def __init__(self, system_application_output):
        """
        Constructor.
            Create an internal SystemApplicationUploadObject from the passed parameter.
        Args:
            system_application_output (list[str]): a list of strings representing the output of the
            'system application-upload' command. Since the command's output is formatted as a table in the CLI, each row
             of the table is represented as an element in this list.

        """
        system_vertical_table_parser = SystemVerticalTableParser(system_application_output)
        output_values = system_vertical_table_parser.get_output_values_dict()
        self.system_application_object = SystemApplicationObject()

        if 'active' in output_values:
            self.system_application_object.set_active(output_values['active'])

        if 'app_version' in output_values:
            self.system_application_object.set_app_version(output_values['app_version'])

        if 'created_at' in output_values:
            self.system_application_object.set_created_at(output_values['created_at'])

        if 'manifest_file' in output_values:
            self.system_application_object.set_manifest_file(output_values['manifest_file'])

        if 'manifest_name' in output_values:
            self.system_application_object.set_manifest_name(output_values['manifest_name'])

        if 'name' in output_values:
            self.system_application_object.set_name(output_values['name'])

        if 'progress' in output_values:
            self.system_application_object.set_progress(output_values['progress'])

        if 'status' in output_values:
            self.system_application_object.set_status(output_values['status'])

        if 'updated_at' in output_values:
            self.system_application_object.set_updated_at(output_values['updated_at'])

    def get_system_application_object(self) -> SystemApplicationObject:
        """
        Getter for SystemApplicationObject object.

        Returns:
            A SystemApplicationObject instance representing the output of commands sucha as 'system application-upload',
            'system application-apply', and others.

        """
        return self.system_application_object
