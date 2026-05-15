#!/bin/bash

CPU_SET=$(taskset -pc 1 | sed -e 's/pid 1.s current affinity list://g' | cut -d',' -f1 | cut -d'-' -f1)
IDX=0
for d in $(lspci -d {{vf_vendor_id}}:{{vf_device_id}} | cut -d' ' -f1) ; do

{% if (pfDriver == 'vfio-pci') and (vfDriver == 'vfio-pci') %}
/usr/local/bin/dpdk-test-bbdev --vfio-vf-token=02bddbbf-bbb0-4d79-886b-91bad3fbb510 --file-prefix=bbdev$IDX -l $CPU_SET -a $d -- -c validation -v /usr/local/share/dpdk/app/test-bbdev/ldpc_dec_default.data
{% else %}
/usr/local/bin/dpdk-test-bbdev --file-prefix=bbdev$IDX -l $CPU_SET -a $d -- -c validation -v /usr/local/share/dpdk/app/test-bbdev/ldpc_dec_default.data
{% endif %}
  IDX=$((IDX+1))
done