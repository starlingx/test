import os

import yaml

from framework.ssh.ssh_connection import SSHConnection
from keywords.files.file_keywords import FileKeywords


class HostProfileYamlKeywords:
    """
    This class is responsible for processing the host profile YAML files.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

        """
        self.ssh_connection = ssh_connection

    def edit_yaml_spec_storage(self, searched_metadata: str, fs: str, size: int, remote_filename: str):
        """Edit storage specs for the desired filesystem.

        Args:
            searched_metadata (str): Metadata to be searched.
            fs (str): Desired filesystem to be modified.
            size (int): Desired size to be set.
            remote_filename (str): Name of the output file.
        """
        local_filename = self.download_file(remote_filename)
        with open(local_filename) as stream:
            list_doc = list(yaml.safe_load_all(stream))

        for document in list_doc:
            if "metadata" in document.keys():
                try:
                    metadata = document["metadata"]
                    if "name" in metadata.keys():
                        metadata_name = document["metadata"]["name"]
                        if metadata_name == searched_metadata:
                            for item in document["spec"]["storage"]["filesystems"]:
                                if item["name"] == fs:
                                    item["size"] = size
                except TypeError:
                    pass

        if "status" not in list_doc[-1].keys():
            list_doc[-1]["status"] = {"deploymentScope": "principal"}

        self.write_yaml(list(list_doc), local_filename)
        self.upload_file(local_filename, remote_filename)

    def write_yaml(self, yaml_data: list, output_filename: str):
        """Writes the received data to a yaml file.

        Args:
            yaml_data (list): Output data received after being modified.
            output_filename (str): Name of the file to be saved.

        """
        with open(output_filename, "w") as f:
            yaml.safe_dump_all(yaml_data, f)

    def download_file(self, file: str) -> str:
        """Downloads the desired file from remote.

        Args:
            file (str): Path to file to be downloaded.

        Returns:
            str: Local path to downloaded file.

        """
        filename = file.split("/")[-1]
        FileKeywords(ssh_connection=self.ssh_connection).download_file(file, f"{filename}")
        return filename

    def upload_file(self, local_file: str, remote_file: str):
        """Uploads the modified file to remote and removes the local copy.

        Args:
            local_file (str): Local file to be uploaded.
            remote_file (str): Remote file name.
        """
        FileKeywords(self.ssh_connection).upload_file(local_file, remote_file)
        os.remove(local_file)

    def update_yaml_key(self, yaml_file: str, key: str, new_value: str) -> None:
        """
        Update a key in a YAML file.

        Args:
            yaml_file (str): Path to the YAML file.
            key (str): The key to update.
            new_value (str): New value to assign to the key.
        """
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)

        if key not in data:
            raise KeyError(f"Key '{key}' not found in {yaml_file}")

        data[key] = new_value

        with open(yaml_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False)

    def remove_yaml_key(self, yaml_file: str, key: str) -> None:
        """
        Remove a key from a YAML file if it exists.

        Args:
            yaml_file (str): Path to the YAML file.
            key (str): The key to remove.
        """
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)

        data.pop(key, None)

        with open(yaml_file, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False)

    def write_dict_yaml(self, data: dict, output_filename: str):
        """
        Writes a yaml file with data formatted as dict

        Args:
            data (dict): data formatted as dict.
            output_filename (str): file name
        """
        with open(output_filename, 'w') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)
