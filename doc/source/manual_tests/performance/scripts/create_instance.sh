#!/bin/bash

# This script has to be executed in the controller.

CLOUD_IMAGE="debian-9.9.5-20190721-openstack-amd64.qcow2"
TEST_IMAGE="debian"
TEST_KEY_NAME="stx-key-test"
DEBIAN_CLOUD_URL="http://cdimage.debian.org/cdimage/openstack/9.9.5-20190721"
TEST_FLAVOR="f2.small"
TEST_NETWORK="network-1"
INSTANCE_NAME="$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 10 ; echo '')"
TIMEOUT=300

if [ -z "$OS_CLOUD" ]; then
    export OS_CLOUD=openstack_helm
fi

# Verify if the controller already has a SSH key.
if [ ! -f "$HOME/.ssh/id_rsa" ]; then
    ssh-keygen -t rsa -N "" -f $HOME/.ssh/id_rsa
fi

if [ -z "$(openstack keypair list | grep -wo $TEST_KEY_NAME)" ]; then
    openstack keypair create \
        --public-key $HOME/.ssh/id_rsa.pub \
        $TEST_KEY_NAME
else
    echo "key: $TEST_KEY_NAME OK"
fi

# Verify OpenStack image.
# This section looks for a debian image, this is
# because the cirrOS image did not work.
if [ -z "$(openstack image list -c Name | grep -w $TEST_IMAGE)" ]; then
    echo "image: $TEST_IMAGE no found"
    echo "$TEST_IMAGE will be installed"
    if [ ! -f "$CLOUD_IMAGE" ]; then
        curl -OL "${DEBIAN_CLOUD_URL}/${CLOUD_IMAGE}"
    fi

    openstack image create \
        --file $CLOUD_IMAGE \
        --disk-format qcow2 \
        --property hw:mem_page_size=large \
        --public $TEST_IMAGE
else
    echo "image: $TEST_IMAGE OK"
fi

# Verify customized flavor
if [ -z "$(openstack flavor list -c Name | grep -w $TEST_FLAVOR)" ]; then
    openstack flavor create \
        --ram 2048 \
        --disk 20 \
        --vcpus 1 \
        --public \
        --id auto \
        --property hw:mem_page_size=large $TEST_FLAVOR
else
    echo "flavor: $TEST_FLAVOR OK"
fi

# Verify network
if [ -z "$(openstack network list -c Name | grep -w $TEST_NETWORK)" ]; then
    echo "Create $TEST_NETWORK"
    openstack network create $TEST_NETWORK
    # Configure subnets
    openstack subnet create \
        --network $TEST_NETWORK \
        --subnet-range 192.168.0.0/24 \
        --ip-version 4 \
        --dhcp subnet-1
else
    echo "network: $TEST_NETWORK OK"
fi

# Create instance using the image, flavor and network verified before
TEST_NETWORK_ID="$(openstack network list --name=$TEST_NETWORK -c ID -f value)"
echo "Launch instance ..."
openstack server create \
    --image $TEST_IMAGE \
    --flavor $TEST_FLAVOR \
    --nic net-id=$TEST_NETWORK_ID \
    --config-drive true \
    --key-name $TEST_KEY_NAME \
    $INSTANCE_NAME

if [ $? -ne 0 ]; then
    echo "error: $INSTANCE_NAME no created"
    exit 1;
fi

for (( count=0; i<${TIMEOUT}; count++ )); do
    INSTANCE_STATUS="$(openstack server list \
            --name=$INSTANCE_NAME -c Status -f value)"
    if [ "$INSTANCE_STATUS" == "ACTIVE" ]; then
        echo "new instance status: $INSTANCE_STATUS"
        break;
    fi
    echo "wait for active instance, current status: $INSTANCE_STATUS"
done

if [ "$(( $TIMEOUT - 1 ))" -eq "$count" ]; then
    echo "error: someting was wrong timeout expired!"
    exit 1
fi

COMPUTE="$(openstack server show \
    -c OS-EXT-SRV-ATTR:host -f value $INSTANCE_NAME)"

echo "The instance $INSTANCE_NAME was created successfully in $COMPUTE"

exit 0

