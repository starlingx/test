from keywords.base_keyword import BaseKeyword


class DockerLoginKeywords(BaseKeyword):
    """
    Class for Docker login keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def login(self, user_name: str, password: str, registry_name: str):
        """
        Logs in to docker
        Args:
            user_name (): the user name
            password (): the password
            registry_name (): the registry name

        Returns:

        """
        self.ssh_connection.send_as_sudo(f'docker login -u {user_name} -p {password} {registry_name}')
