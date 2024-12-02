# This utility file contains functions to help the code find the path to resource files
# when starlingx gets used as a submodule, or from outside code.
from pathlib import Path


def get_stx_resource_path(relative_path: str) -> str:
    """
    This function will get the full path to the resource from the relative_path provided.
    This will allow projects that use StarlingX as a submodule to still find resource files using the relative path.
    
    Args:
        relative_path: The relative path to the resource.
        
    Returns: The full path to the resource
    
    Example:
        >>> get_resource_path("framework/resources/resource_finder.py")
        will return /home/user/repo/starlingx/framework/resources/resource_finder.py
    """

    path_of_this_file = Path(__file__)
    root_folder_of_stx = path_of_this_file.parent.parent.parent
    path_to_resource = f"{str(root_folder_of_stx)}/{relative_path}"

    return path_to_resource


