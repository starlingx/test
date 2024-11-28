from keywords.linux.dpkg.object.dpkg_status_object import DpkgStatusObject


class DpkgStatusOutput:
    """
    This class parses the output of 'dpkg -s' commands into a list of DpkgStatusObjects
    """

    def __init__(self, dpkg_status_output: str):
        """
        Constructor

        Args:
            dpkg_status_output: String output of 'dpkg -s' command
        """

        self.dpkg_status_object: DpkgStatusObject = DpkgStatusObject()

        line_header = None

        for line in dpkg_status_output:

            # Lines are of the form "Package: isolcpus-device-plugin"
            if ":" in line:
                split_line = line.split(":")
                line_header = split_line[0]
                line_value = split_line[1].strip()
            else:
                # This is the continuation of the last line.
                line_value = line.strip()

            if line_header == "Package":
                self.dpkg_status_object.set_package(line_value)
            elif line_header == "Status":
                self.dpkg_status_object.set_status(line_value)
            elif line_header == "Priority":
                self.dpkg_status_object.set_priority(line_value)
            elif line_header == "Section":
                self.dpkg_status_object.set_section(line_value)
            elif line_header == "Installed-Size":
                self.dpkg_status_object.set_installed_size(int(line_value))
            elif line_header == "Maintainer":
                self.dpkg_status_object.set_maintainer(line_value)
            elif line_header == "Architecture":
                self.dpkg_status_object.set_architecture(line_value)
            elif line_header == "Version":
                self.dpkg_status_object.set_version(line_value)
            elif line_header == "Depends":
                self.dpkg_status_object.set_depends(line_value)
            elif line_header == "Description":
                self.dpkg_status_object.append_description(line_value)
            elif line_header == "Homepage":
                self.dpkg_status_object.set_homepage(line_value)

    def get_status_object(self) -> DpkgStatusObject:
        """
        Getter for the DpkgStatusObject parsed from the command output.
        Returns: DpkgStatusObject

        """
        return self.dpkg_status_object
