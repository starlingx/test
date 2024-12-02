import os

from framework.resources import resource_finder


def test_resource_finder():
    """
   Verify that the resource_finder can find the full path to the resources appropriately.
    """

    resource_full_path = resource_finder.get_stx_resource_path("framework/resources/resource_finder.py")
    assert os.path.isfile(resource_full_path)
