###
#
# Copyright (c) 2020 Intel Corporation
#
# SPDX-License-Identifier: Apache-2.0
#
# Test measurements for metric
# Author(s): Mihail-Laurentiu Trica mihai-laurentiu.trica@intel.com
###

import os
from pytest import mark, fixture

from consts.stx import GuestImages
from keywords import glance_helper

VM_IDS = list()
cirros_params = {
    "image_name": "cirros",
    "image_name_tmp": "cirros-tmp",
    "image_file": os.path.join(GuestImages.DEFAULT["image_dir"], "cirros-0.4.0-x86_64-disk.img"),
    "disk_format": "qcow2",
    "flavor_disk": 10,
    "flavor_ram": 20
}

second_update = None


# Create Image For Metrics
@fixture(scope="module")
@mark.robotsanity
def create_image_for_metrics():
    """
    Create an image that will be used by tests in the suite (with or without properties)
    to be used to launch Cirros instances
    """
    image_id = glance_helper.create_image(
        name=cirros_params['image_name'],
        source_image_file=cirros_params['image_file'],
        disk_format=cirros_params['disk_format'],
        cleanup="module")[1]
    return image_id


# Update image name
@mark.robotsanity
def test_update_image_name(create_image_for_metrics):
    """
    Test for Update image name
    """
    global second_update
    # This workaround is needed because it seems that the output is not a string, but a list
    # and needs to be converted to a string
    created_at = glance_helper.get_image_values(create_image_for_metrics, "created_at")
    # Set temporary image name
    test_image_name = glance_helper.set_image(
        image=create_image_for_metrics,
        new_name=cirros_params['image_name_tmp'])[1]
    # ToDo: modify glance_helper.set_image to add imageID as an output
    test_image_name = test_image_name.replace("Image ", "")
    test_image_name = test_image_name.replace(" is successfully modified", "")
    first_update = glance_helper.get_image_values(test_image_name, "updated_at")
    assert created_at != first_update, "date of first update should be different" \
                                       " than date of creation time"
    # Check temporary image name
    image_exists = glance_helper.image_exists(
        image=cirros_params['image_name_tmp'],
        image_val="Name")
    assert image_exists is True, "Image name has not been changed to {}"\
        .format(cirros_params['image_name_tmp'])
    # Set original image name
    test_image_name = glance_helper.set_image(
        image=create_image_for_metrics,
        new_name=cirros_params['image_name'])[1]
    # ToDo: modify glance_helper.set_image to add imageID as an output
    test_image_name = test_image_name.replace("Image ", "")
    test_image_name = test_image_name.replace(" is successfully modified", "")
    second_update = glance_helper.get_image_values(test_image_name, "updated_at")
    assert first_update != second_update, "date of second update should be different" \
                                          "than date of first update"
    # Check image name is back to original name
    image_exists = glance_helper.image_exists(
        image=cirros_params['image_name'],
        image_val="Name")
    assert image_exists is True, "Image name has not been changed back to {}".\
        format(cirros_params['image_name'])


# Update Image Disk Ram Size
@mark.robotsanity
def test_update_image_disk_ram_size(create_image_for_metrics):
    """
    Test for Update image disk and RAM size
    """
    # Set min disk size
    test_image_name = glance_helper.set_image(
        image=create_image_for_metrics,
        min_disk=10)[1]
    # ToDo: modify glance_helper.set_image to add imageID as an output
    test_image_name = test_image_name.replace("Image ", "")
    test_image_name = test_image_name.replace(" is successfully modified", "")
    third_update = glance_helper.get_image_values(test_image_name, "updated_at")
    assert second_update != third_update, "date of third update should be different" \
                                          "than date of second update"
    # Set min ram size
    test_image_name = glance_helper.set_image(
        image=create_image_for_metrics,
        min_ram=20)[1]
    # ToDo: modify glance_helper.set_image to add imageID as an output
    test_image_name = test_image_name.replace("Image ", "")
    test_image_name = test_image_name.replace(" is successfully modified", "")
    forth_update = glance_helper.get_image_values(test_image_name, "updated_at")
    assert third_update != forth_update, "date of forth update should be different " \
                                         "than date of third update"
