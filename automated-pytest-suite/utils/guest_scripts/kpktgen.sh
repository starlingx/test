#! /bin/sh

modprobe pktgen

function pgset() {
    local result

    echo $1 > $PGDEV

    result=`cat $PGDEV | fgrep "Result: OK:"`
    if [ "$result" = "" ]; then
         cat $PGDEV | fgrep Result:
    fi
}

function pg() {
    echo inject > $PGDEV
    cat $PGDEV
}

# Config Start Here -----------------------------------------------------------


# thread config
# Each CPU has own thread. Two CPU exammple. We add eth1, eth2 respectivly.

# setup_netif_multiqueue "eth1"
ethtool -G eth1 tx 1024
PGDEV=/proc/net/pktgen/kpktgend_1
  echo "Removing all devices"
 pgset "rem_device_all"
  echo "Adding eth1"
 pgset "add_device eth1"
  echo "Setting max_before_softirq 10000"
 pgset "max_before_softirq 10000"

# We need to remove old config since we dont use this thread. We can only
# one NIC on one CPU due to affinity reasons.

# Guest might be launched with less than 2 vcpus, ignore other threads
# PGDEV=/proc/net/pktgen/kpktgend_1
#   echo "Removing all devices"
#  pgset "rem_device_all"

# device config
# ipg is inter packet gap. 0 means maximum speed.

CLONE_SKB="clone_skb 0"
# NIC adds 4 bytes CRC
PKT_SIZE="pkt_size 60"

# COUNT 0 means forever
#COUNT="count 0"
COUNT="count 0"

# rate 300M means 300Mb/s
RATE=""

DST_IP="dst 10.10.11.2"
DST_MAC="dst_mac  00:04:23:08:91:dc"
source /root/kpktgen.config

PGDEV=/proc/net/pktgen/eth1
  echo "Configuring $PGDEV"
 pgset "$COUNT"
 pgset "$CLONE_SKB"
 pgset "$PKT_SIZE"
 pgset "$DST_IP"
 pgset "$DST_MAC"
 if [ -n "$RATE" ]; then
    pgset "$RATE"
 fi

# Time to run
PGDEV=/proc/net/pktgen/pgctrl

 echo "Running... ctrl^C to stop"
 pgset "start"
 echo "Done"

# Result can be vieved in /proc/net/pktgen/eth1
