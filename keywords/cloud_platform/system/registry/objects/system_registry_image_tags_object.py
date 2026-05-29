class SystemRegistryImageTagsObject:
    """Represents one row of `system registry-image-tags <image>` output.

    The command renders one tag per row in a single-column table:

    +-----------+
    | Image Tag |
    +-----------+
    | 26.09-0   |
    | 26.03-0   |
    +-----------+
    """

    def __init__(self, image_tag: str):
        """Constructor.

        Args:
            image_tag (str): The image tag.
        """
        self.image_tag = image_tag

    def get_image_tag(self) -> str:
        """Getter for image tag.

        Returns:
            str: The image tag.
        """
        return self.image_tag
