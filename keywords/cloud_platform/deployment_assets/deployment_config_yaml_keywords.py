from typing import Optional, TextIO, Union

import yaml

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.deployment_assets.host_profile_yaml_keywords import HostProfileYamlKeywords


class DeploymentConfigYamlKeywords(BaseKeyword):
    """
    This class edits resources in a Deployment Manager deployment config YAML file (e.g. deployment-config.yaml).

    Every edit also sets 'status.deploymentScope' on the resource. The Deployment Manager only
    reconciles a day-2 change for a resource that declares the 'principal' scope.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

        """
        self.ssh_connection = ssh_connection
        self.yaml_file_keywords = HostProfileYamlKeywords(ssh_connection)

    def update_resource(self, remote_filename: str, kind: str, name: str, spec: Optional[dict] = None, scope: str = "principal"):
        """Update the spec and deployment scope of a resource in the remote deployment config file.

        Args:
            remote_filename (str): Path of the deployment config file on the controller.
            kind (str): Kind of the resource, e.g. "DataNetwork".
            name (str): Name of the resource.
            spec (Optional[dict]): Values merged into 'spec'. If None or empty, 'spec' is left untouched.
            scope (str): Deployment scope to set, "principal" or "bootstrap".

        Raises:
            KeywordException: If the file has no resource with that kind and name.
        """
        local_filename = self.yaml_file_keywords.download_file(remote_filename)
        with open(local_filename) as stream:
            documents = self.load_documents(stream)

        self.update_resource_in_documents(documents, kind, name, spec, scope, remote_filename)

        self.yaml_file_keywords.write_yaml(documents, local_filename)
        self.yaml_file_keywords.upload_file(local_filename, remote_filename)

    def has_resource(self, remote_filename: str, kind: str, name: str) -> bool:
        """Check if the remote deployment config file has a resource with that kind and name.

        Args:
            remote_filename (str): Path of the deployment config file on the controller.
            kind (str): Kind of the resource, e.g. "DataNetwork".
            name (str): Name of the resource.

        Returns:
            bool: True if the file has the resource.
        """
        local_filename = self.yaml_file_keywords.download_file(remote_filename)
        with open(local_filename) as stream:
            documents = self.load_documents(stream)

        return any(isinstance(document, dict) and document.get("kind") == kind and document.get("metadata", {}).get("name") == name for document in documents)

    def add_resources(self, remote_filename: str, resources: list[dict]):
        """Add resources to the remote deployment config file, replacing any with the same kind and name.

        Args:
            remote_filename (str): Path of the deployment config file on the controller.
            resources (list[dict]): Complete resource documents to add.
        """
        local_filename = self.yaml_file_keywords.download_file(remote_filename)
        with open(local_filename) as stream:
            documents = self.load_documents(stream)

        documents = self.add_resources_to_documents(documents, resources)

        self.yaml_file_keywords.write_yaml(documents, local_filename)
        self.yaml_file_keywords.upload_file(local_filename, remote_filename)

    def load_documents(self, stream: Union[str, TextIO]) -> list:
        """Load the YAML documents of a deployment config, skipping empty ones.

        A deployment config usually starts with '---', which gives an empty first document. An empty
        document would be written back as 'null', which kubectl rejects as an invalid document separator.

        Args:
            stream (Union[str, TextIO]): Open file, or string, with the YAML content.

        Returns:
            list: The non-empty YAML documents.
        """
        return [document for document in yaml.safe_load_all(stream) if document]

    def update_resource_in_documents(self, documents: list, kind: str, name: str, spec: Optional[dict], scope: str, source_name: str = "deployment config"):
        """Update the spec and deployment scope of a resource in a list of YAML documents, in place.

        Args:
            documents (list): YAML documents of the deployment config.
            kind (str): Kind of the resource.
            name (str): Name of the resource.
            spec (Optional[dict]): Values merged into 'spec'. If None or empty, 'spec' is left untouched.
            scope (str): Deployment scope to set.
            source_name (str): Name of the file, for error reporting.

        Raises:
            KeywordException: If no document has that kind and name.
        """
        resource_found = False

        for document in documents:
            if not isinstance(document, dict):
                continue
            if document.get("kind") != kind or document.get("metadata", {}).get("name") != name:
                continue

            resource_found = True
            document.setdefault("status", {})["deploymentScope"] = scope
            if spec:
                document.setdefault("spec", {}).update(spec)
            get_logger().log_info(f"Updated {kind} {name} in {source_name}: scope={scope}, spec={spec}")

        if not resource_found:
            raise KeywordException(f"No {kind} named '{name}' was found in {source_name}.")

    def add_resources_to_documents(self, documents: list, resources: list[dict]) -> list:
        """Add resources to a list of YAML documents, replacing any with the same kind and name.

        Args:
            documents (list): YAML documents of the deployment config.
            resources (list[dict]): Complete resource documents to add.

        Returns:
            list: The documents with the resources added.
        """
        added = {(resource.get("kind"), resource.get("metadata", {}).get("name")) for resource in resources}
        kept = [document for document in documents if not (isinstance(document, dict) and (document.get("kind"), document.get("metadata", {}).get("name")) in added)]
        return kept + list(resources)
