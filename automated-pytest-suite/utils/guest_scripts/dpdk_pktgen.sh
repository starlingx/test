#!/bin/bash

# the original version from /usr/local/bin/launch_pktgen.sh
# written by Allain Legacy

sleep 60

PKTGEN=${PKTGEN:-/usr/local/bin/pktgen}
HUGETLBMNT=${HUGETLBMNT:-/dev/hugepages}

# Assumes 3 nic guest, with first nic virtio
# using only the first nic
DEVICES=("0000:00:04.0")

## Automatically unbind/rebind PCI devices
modprobe igb_uio
USEDEVICES=""
for DEVICE in ${DEVICES[@]}; do
    UIO_DRIVER=/sys/bus/pci/drivers/igb_uio
    SYSFS=/sys/bus/pci/devices/${DEVICE}

    if [ ! -d ${SYSFS} ]; then
        echo "Unable to find device directory: ${SYSFS}"
        exit 1
    fi

    # Add the device to the list of supported devices of the UIO driver
    UEVENT=${SYSFS}/uevent
    PCI_ID=($(cat ${UEVENT} | grep PCI_ID | sed -e 's/^.*=//' | tr ":" " "))
    echo "${PCI_ID[0]} ${PCI_ID[1]}" > ${UIO_DRIVER}/new_id

    # Unbind from the old driver and bind to the new driver
    echo -n ${DEVICE} > ${SYSFS}/driver/unbind
    echo -n ${DEVICE} > ${UIO_DRIVER}/bind
    USEDEVICES+=" --pci-whitelist ${DEVICE}"
done

# cpu mask cannot be set for lcores not exist on the system
# 2vcpus setup
# ${PKTGEN} -c 0x3 -n 1 --huge-dir ${HUGETLBMNT} --proc-type primary
# --socket-mem 512 ${USEDEVICES} --file-prefix pg -- -p 0xFFFF -P -N
# -m "[1:1].0" -f /root/dpdk_pktgen.config

# 3vcpus setup
${PKTGEN} -c 0x7 -n 2 --huge-dir ${HUGETLBMNT} --proc-type primary \
--socket-mem 512 ${USEDEVICES} --file-prefix pg -- -p 0xFFFF -P -N \
-m "[1:1-2].0" -f /root/dpdk_pktgen.config

exit $?
