import json5
from config.docker.objects.registry import Registry


class DockerConfig:
    """
    Class to hold configuration of the Cloud Platform's Docker Registries
    """

    def __init__(self, config):
        self.registry_list: [Registry] = []
        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the docker config file: {config}")
            raise

        docker_dict = json5.load(json_data)
        for registry in docker_dict['registries']:
            registry_dict = docker_dict['registries'][registry]
            reg = Registry(registry_dict['registry_name'], registry_dict['registry_url'], registry_dict['user_name'], registry_dict['password'])
            self.registry_list.append(reg)

    def get_registry(self, registry_name) -> Registry:
        """
        Getter for the KUBECONFIG environment variable on the lab where we want to run.
        """

        registries = list(filter(lambda registry: registry.get_registry_name() == registry_name, self.registry_list))
        if not registries:
            raise ValueError(f"No registry with the name {registry_name} was found")
        return registries[0]
