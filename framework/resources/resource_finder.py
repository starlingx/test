# This utility file contains functions to help the code find the path to resource files
# when starlingx gets used as a submodule, or from outside code.
import os.path
from pathlib import Path


def get_stx_repo_root() -> str:
    """
    Find the full path to the repository root.

    Uses the position of the current file relative to the root of the repo.

    Returns:
        str: The absolute path to the repository root.

    Example:
        >>> get_repo_root()
        will return /home/user/repo/starlingx
    """
    path_of_this_file = Path(__file__)

    # This file is in framework/resources/resource_finder.py, so go up 3 levels
    root_folder = path_of_this_file.parent.parent.parent
    return root_folder.as_posix()


def get_stx_resource_path(relative_path: str) -> str:
    """
    This function will get the full path to the resource from the relative_path provided.

    This will allow projects that use StarlingX as a submodule to still find resource files using the relative path.

    Args:
        relative_path (str): The relative path to the resource.

    Returns:
        str: The full path to the resource.

    Example:
        >>> get_resource_path("framework/resources/resource_finder.py")
        will return /home/user/repo/starlingx/framework/resources/resource_finder.py
    """
    # check to see if the path really is relative, if not just return the path
    if os.path.isabs(relative_path):
        return relative_path
    root_folder_of_stx = get_stx_repo_root()
    path_to_resource = Path(root_folder_of_stx, relative_path).as_posix()

    return path_to_resource
