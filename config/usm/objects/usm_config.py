import json5


class UsmConfig:
    """
    Class to hold configuration for USM upgrade/patch tests.
    """

    def __init__(self, config):
        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the USM config file: {config}")
            raise

        usm_dict = json5.load(json_data)
        self.usm_is_upgrade = usm_dict.get("usm_is_upgrade", None)
        self.usm_is_patch = usm_dict.get("usm_is_patch", None)
        self.iso_path = usm_dict.get("iso_path", None)
        self.upgrade_license = usm_dict.get("upgrade_license", None)
        self.patch_path = usm_dict.get("patch_path", None)
        self.patch_dir = usm_dict.get("patch_dir", None)
        self.dest_dir = usm_dict.get("dest_dir", None)
        self.build_server = usm_dict.get("build_server", None)
        self.build_server_username = usm_dict.get("build_server_username", None)
        self.build_server_password = usm_dict.get("build_server_password", None)
        self.upgrade_arguments = usm_dict.get("upgrade_arguments", None)
        self.to_release_ids = usm_dict.get("to_release_ids", None)
        self.extra_attributes = usm_dict.get("extra_attributes", {})

    def get_usm_is_upgrade(self) -> str:
        """
        Getter for the usm_is_upgrade

        Indicates the current operation is for Major rel upgrade

        Returns:
            str: the usm_is_upgrade
        """
        return self.usm_is_upgrade

    def get_usm_is_patch(self) -> str:
        """
        Getter for the usm_is_patch

        Indicates the current operation is patching the system.

        Returns:
            str: the usm_is_patch
        """
        return self.usm_is_patch

    def get_iso_path(self) -> str:
        """
        Getter for the iso_path

        Absolute path to ISO for Major rel upgrade

        Returns:
            str: the iso_path
        """
        return self.iso_path

    def get_upgrade_license(self) -> str:
        """
        Getter for the upgrade_license

        Absolute path to the Signature path for Major rel upgrade.

        Returns:
            str: the upgrade_license
        """
        return self.upgrade_license

    def get_patch_path(self) -> str:
        """
        Getter for the patch_path

        Absolute path to the .patch file for Patching.

        Returns:
            str: the patch_path
        """
        return self.patch_path

    def get_patch_dir(self) -> str:
        """
        Getter for the patch_dir

        Path of directory where one or more .patch files are located.

        Returns:
            str: the patch_dir
        """
        return self.patch_dir

    def get_dest_dir(self) -> str:
        """
        Getter for the dest_dir

        Directory on the lab where the files need to be stored.

        Returns:
            str: the dest_dir
        """
        return self.dest_dir

    def get_build_server(self) -> str:
        """
        Getter for the build_server

        Address of the server where the iso/patch files are located.

        Returns:
            str: the build_server
        """
        return self.build_server

    def get_build_server_username(self) -> str:
        """
        Getter for the build_server_username

        Username to authenticate to build_server

        Returns:
            str: the build_server_username
        """
        return self.build_server_username

    def get_build_server_password(self) -> str:
        """
        Getter for the build_server_password

        Password to authenticate to build_server

        Returns:
            str: the build_server_password
        """
        return self.build_server_password

    def get_upgrade_arguments(self) -> str:
        """
        Getter for the upgrade_arguments

        Arguments for upgrade/patching testing

        Returns:
            str: the upgrade_arguments
        """
        return self.upgrade_arguments

    def get_to_release_ids(self) -> str:
        """
        Getter for the to_release_ids

        Release ids (one or more) to which the system is upgraded. Used for either multiple patches or major release + patch(es)

        Returns:
            str: the to_release_ids
        """
        return self.to_release_ids

    def get_extra_attributes(self) -> dict:
        """
        Getter for the extra_attributes

        Some extra attributes for patching USM, config

        Returns:
            dict: the extra_attributes
        """
        return self.extra_attributes
