class SystemRegistryImageListObject:
    """Represents one row of `system registry-image-list` output.

    The command renders one image per row in a single-column table:

    +------------------------------------------------------------+
    | Image Name                                                 |
    +------------------------------------------------------------+
    | docker.io/wra/elasticsearch                                |
    | docker.io/wra/kibana                                       |
    +------------------------------------------------------------+
    """

    def __init__(self, image_name: str):
        """Constructor.

        Args:
            image_name (str): The full registry image name.
        """
        self.image_name = image_name

    def get_image_name(self) -> str:
        """Getter for image name.

        Returns:
            str: The full registry image name.
        """
        return self.image_name
