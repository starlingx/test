"""Tests of the netapp-storage application on the ONTAP NAS (NFS) backend."""

from pytest import FixtureRequest, mark

from testcases.cloud_platform.apps_setup.netapp_storage.helper_netapp_storage import NETAPP_NFS_CAPABILITY, reboot_active_controller_with_continuous_write


@mark.p2
@mark.lab_has_netapp_nfs
@mark.lab_has_standby_controller
def test_netapp_nfs_reboot_active_controller(request: FixtureRequest) -> None:
    """
    Reboot the active controller and verify the NetApp NFS backend before and after,
    while a pod keeps continuously writing to an ontap-nas volume.

    Test Steps:
        - Check the netapp-storage integrity before the reboot: application applied,
          trident pods healthy and the ontap-nas backend reporting Success
        - Get the NFS storage class name from the lab
        - Start a continuous-write pod on an NFS (RWX) volume, pinned to the standby
          controller so it stays up while the active controller is rebooted, reusing
          the pod when one is already running there
        - Record the pod write-cycle count before the reboot
        - Force reboot the active controller and wait until it is available again
        - Swact back so the original controller is active again
        - Verify the writer pod is still Running
        - Verify its write-cycle count advanced, i.e. the volume stayed writable
        - Check the netapp-storage integrity after the reboot

    Teardown:
        - Delete the continuous-write pod and its PVC, waiting for the PVC to be gone,
          and remove the uploaded YAML files from the active controller

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    reboot_active_controller_with_continuous_write(request, NETAPP_NFS_CAPABILITY)
