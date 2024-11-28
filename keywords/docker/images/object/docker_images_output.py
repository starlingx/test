from keywords.docker.images.object.docker_images_object import DockerImagesObject
from keywords.docker.images.object.docker_images_table_parser import DockerImagesTableParser


class DockerImagesOutput:

    def __init__(self, docker_images_output: str):
        """
        Constructor

        Args:
            docker_images_output: Raw string output from running a "docker images" command.

        """

        self.docker_images_output: [DockerImagesObject] = []
        docker_images_table_parser = DockerImagesTableParser(docker_images_output)
        output_values_list = docker_images_table_parser.get_output_values_list()

        for image_dict in output_values_list:

            if 'REPOSITORY' not in image_dict:
                raise ValueError(f"There is no Repository associated with the docker image: {image_dict}")

            docker_image = DockerImagesObject(image_dict['REPOSITORY'])

            if 'TAG' in image_dict:
                docker_image.set_tag(image_dict['TAG'])

            if 'IMAGE ID' in image_dict:
                docker_image.set_image_id(image_dict['IMAGE ID'])

            if 'CREATED' in image_dict:
                docker_image.set_created(image_dict['CREATED'])

            if 'SIZE' in image_dict:
                docker_image.set_size(image_dict['SIZE'])

            self.docker_images_output.append(docker_image)

    def get_images(self) -> [DockerImagesObject]:
        """
        This function will get the list of all images available.

        Returns: List of DockerImagesObject

        """
        return self.docker_images_output
