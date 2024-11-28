from keywords.docker.docker_table_parser_base import DockerTableParserBase


class DockerImagesTableParser(DockerTableParserBase):
    """
    Class for parsing the output of "docker images" commands.
    """

    def __init__(self, docker_output):
        """
        Constructor
        Args:
            docker_output: The raw String output of a docker command that returns a table.
        """

        super().__init__(docker_output)
        self.possible_headers = [
            "REPOSITORY",
            "TAG",
            "IMAGE ID",
            "CREATED",
            "SIZE",
        ]
