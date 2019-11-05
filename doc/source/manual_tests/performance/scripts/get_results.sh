#!/bin/bash

INSTANCE_NAME="$1"

if [ -z "$INSTANCE_NAME" ]; then
    echo "error: instance no specified."
    exit 1;
fi

if [ -z "$(openstack server list --name $INSTANCE_NAME -c ID -f value)" ]; then
    echo "error: $INSTANCE_NAME no found"
    exit 1
else
    echo "$INSTANCE_NAME: OK"
fi

COMPUTE="$(openstack server show \
    -c OS-EXT-SRV-ATTR:host -f value $INSTANCE_NAME)"

echo "kill QEMU process..."
INIT_TIME=$(echo $(($(date +%s%N)/1000000)))
ssh $COMPUTE sudo pkill qemu
while [ 1 ]; do
    INSTANCE_STATUS="$(openstack server list \
            --name=$INSTANCE_NAME -c Status -f value)"
    if [ "$INSTANCE_STATUS" != "ACTIVE" ]; then
        END_TIME=$(echo $(($(date +%s%N)/1000000)))
        break;
    fi
done

echo "instance status: $INSTANCE_STATUS"
echo "init time (ms): $INIT_TIME"
echo "end  time (ms): $END_TIME"
echo "delta: INIT_TIME=$(echo $(($END_TIME - $INIT_TIME)))"
