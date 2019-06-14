#!/bin/bash
################################################################################
# Copyright (c) 2014-2015 Wind River Systems, Inc.
#
# The right to copy, distribute, modify, or otherwise make use of this
# software may be licensed only pursuant to the terms of an applicable Wind
# River license agreement.
#
################################################################################
# chkconfig: 2345 10 99
PROGRAM="tis_automation_init.sh"

# Default configurations
FUNCTIONS=routing,
LOW_LATENCY='no'
VSWITCH_CMDFILE=/etc/vswitch/vswitch.cmds.default
VSWITCH_INIFILE=/etc/vswitch/vswitch.ini
VSWITCH_CONFIG=/etc/vswitch/vswitch.conf
BRIDGE_PORTS="eth1,eth2.2"
BRIDGE_MTU=1500

# PCI vendor/device IDs
PCI_VENDOR_VIRTIO="0x1af4"
PCI_DEVICE_VIRTIO="0x1000"
PCI_DEVICE_MEMORY="0x1110"
PCI_SUBDEVICE_NET="0x0001"
PCI_SUBDEVICE_AVP="0x1104"

# Default NIC device type
NIC_DEVICE_DEFAULT="${PCI_VENDOR_VIRTIO}:${PCI_DEVICE_MEMORY}:${PCI_SUBDEVICE_AVP}"
NIC_COUNT_DEFAULT=2

################################################################################
# Generate a log to the syslog stream and stdout
################################################################################
function log()
{
    local MESSAGE=$1
    local TEXT="${PROGRAM}: ${MESSAGE}"
    logger ${TEXT}
    echo ${TEXT}
}

function setup_netif_multiqueue()
{
    local IFNAME=$1

    DRIVER=$(basename $(readlink /sys/class/net/${IFNAME}/device/driver))
    if [ "$DRIVER" == "virtio_net" ]; then
        CPU_COUNT=$(cat /proc/cpuinfo |grep "^processor"|wc -l)

        CPU_START=0
        CPU_END=$((CPU_COUNT-1))

        if [ "$LOW_LATENCY" == "yes" ]; then
            # CPU 0 should not be used when configured for low latency
            # since VCPU0 does not run as a realtime thread
            CPU_START=1
            CPU_COUNT=$((CPU_COUNT-1))
        fi

        ethtool -L ${IFNAME} combined $CPU_COUNT

        QUEUE=0
        for ((CPUID=$CPU_START; CPUID <= $CPU_END; CPUID++))
        do
            CPUMASK=$(echo "(2^${CPUID})" | bc -l)
            IFNUMBER=${IFNAME#eth}
            IRQ=$(cat /proc/interrupts | grep "virtio${IFNUMBER}-input.${QUEUE}" \
            | awk '{print $1}' | sed 's/://')
            echo ${CPUMASK} > /proc/irq/${IRQ}/smp_affinity
            QUEUE=$((QUEUE+1))
        done
    fi

    return 0
}

function setup_kernel_routing()
{
    echo 1 > /proc/sys/net/ipv4/ip_forward
    echo 0 > /proc/sys/net/ipv4/conf/default/rp_filter
    echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter
    echo 1 > /proc/sys/net/ipv6/conf/default/forwarding
    echo 1 > /proc/sys/net/ipv6/conf/all/forwarding
    modprobe 8021q
    for IFNAME in $(find /sys/class/net -maxdepth 1 -type l -exec basename {} \\;); do
        if [[ $IFNAME != "lo" ]]; then
            echo "${IFNAME}" | grep -q "\\."
            if [ $? -eq 0 ]; then
                # VLAN is being created, create interface and setup underlying interface
                UIFNAME=$(echo ${IFNAME}|awk -F '.' '{print $1}')
                VLANID=$(echo ${IFNAME}|awk -F '.' '{print $2}')

                # enable multiqueue support if using the virtio-net driver
                setup_netif_multiqueue ${UIFNAME}
            else
                setup_netif_multiqueue ${IFNAME}
            fi
            echo 0 > /proc/sys/net/ipv4/conf/${IFNAME}/rp_filter
            echo 1 > /proc/sys/net/ipv6/conf/${IFNAME}/forwarding
        fi
    done
    return 0
}

## Reload the wrs-avp driver while taking care to only shutdown eth0 if it is
## driven by this driver.  This exception is made because we rarely use an AVP
## device for eth0 and shutting down that interface can interfere with
## automated testing if they were able to SSH in before this step and then get
## kicked out of the SSH session.
##
function reload_wrs_avp_driver()
{
    local ETH0_DRIVER=$(cat /sys/class/net/eth0/device/uevent | grep DRIVER | sed 's#DRIVER=##')

    if [ "${ETH0_DRIVER}" == "wrs_avp" ]; then
        ## Bring down the interface gracefully before unloading the module
        ifdown eth0
    fi

    rmmod wrs_avp
    modprobe wrs_avp

    local RET=0
    if [ "${ETH0_DRIVER}" == "wrs_avp" ]; then
        ## Bring up the interface again
        ifup eth0
        RET=$?
    fi

    return ${RET}
}

## Count the number of 1 bits that are set in an IPv4 byte value.  This
## function assumes that the input value is a proper IPv4 mask byte; meaning
## that all upper bits are 1's and all lower bits are 0's.
##
function count_1bits()
{
   local VALUE=$1
   local COUNT=0

   while [ $((VALUE & 0x80)) -ne 0 ]; do
      VALUE=$((VALUE * 2))
      COUNT=$((COUNT + 1))
   done

   return $COUNT
}

## Convert an IPv4 mask value to a CIDR prefix length.
##
function convert_ipv4_mask_to_length()
{
   local MASK=(${1//./ })

   local LENGTH=0
   for I in $(seq 0 3); do
      local BYTE=${MASK[${I}]}
      if [ ${BYTE} -eq 255 ]; then
         BITS=8
      elif [ ${BYTE} -eq 0 ]; then
         break
      else
         count_1bits ${BYTE}
         BITS=$?
      fi
      LENGTH=$((LENGTH + $BITS))
   done

   return ${LENGTH}
}

## Setup the vswitch offline CLI commands file which is consumed directly by the vswitch
## process to load the logical interface objects
##
function setup_vswitch_layer2_commands_file()
{
    local BRIDGE_PORTS=$1
    local BRIDGE_MTU=$2
    local PCI_UUIDS=("${!3}")
    local NETUUID=$(uuidgen -r)

    echo "## AVS bridge configuration" > ${VSWITCH_CMDFILE}
    echo "##" >> ${VSWITCH_CMDFILE}

    ## Setup a network to connect the bridge ports
    echo "network add default ${NETUUID}" >> ${VSWITCH_CMDFILE}

    PORTS=(${BRIDGE_PORTS//,/ })
    for I in ${!PORTS[@]}; do
        local PORT=${PORTS[${I}]}
        local UUID=${PCI_UUIDS[${I}]}
        local DATA=(${PORT//./ })
        local IFNAME=${DATA[0]}
        local VLANID=${DATA[1]}
        local VLAN_MTU=$((BRIDGE_MTU - 4))

        ## Setup logical interface.
        ##  Note:  we use the same UUID for the port and interface because
        ##  since there is no agents or management software it does not
        ##  matter.
        echo "ethernet add ${UUID} ${UUID} ${BRIDGE_MTU}" >> ${VSWITCH_CMDFILE}

        if [ "0${VLANID}" -ne 0 ]; then
            ## Setup a VLAN interface (if necessary)
            local IFUUID=$(uuidgen -r)
            echo "vlan add ${IFNAME} ${VLANID} ${IFUUID} ${VLAN_MTU}" >> ${VSWITCH_CMDFILE}
        else
            ## Drop the ".0" from the name
            PORT=${IFNAME}
        fi

        ## Attach the logical interface
        echo "bridge attach ${PORT} default" >> ${VSWITCH_CMDFILE}
    done

    echo "quit" >> ${VSWITCH_CMDFILE}
    return 0
}

## Setup the vswitch offline CLI commands file which is consumed directly by the vswitch
## process to load the logical interface objects and setup a layer3 routed environment
##
function setup_vswitch_layer3_commands_file()
{
    local ADDRESSES=("${!1}")
    local ROUTES=("${!2}")
    local PCI_UUIDS=("${!3}")
    local NATARGS=""

    echo "## AVR router configuration" > ${VSWITCH_CMDFILE}
    echo "##" >> ${VSWITCH_CMDFILE}

    ## Enable forwarding on the default router context
    echo "router enable forwarding default" >> ${VSWITCH_CMDFILE}

    for ADDRESS in ${ADDRESSES[@]}; do
        DATA=(${ADDRESS//,/ })
        IPADDR=${DATA[0]}
        IPMASK=${DATA[1]}
        IFNAME=${DATA[2]}
        IFMTU=${DATA[3]}
        IFDATA=(${IFNAME//./ })
        IFNAME=${IFDATA[0]}
        VLANID=${IFDATA[1]}
        IFNUMBER=${IFNAME#eth}
        UUID=${PCI_UUIDS[${IFNUMBER}]}

        ## Shift the array so that the processed elements are removed
        for I in $(seq 0 3); do
            unset DATA[0]
            DATA=(${DATA[@]})
        done

        convert_ipv4_mask_to_length ${IPMASK}
        LENGTH=$?

        ## Setup logical interface.
        ##  Note:  we use the same UUID for the port and interface because
        ##  since there is no agents or management software it does not
        ##  matter.
        echo "ethernet add ${UUID} ${UUID} ${IFMTU}" >> ${VSWITCH_CMDFILE}

        if [ "0${VLANID}" -ne 0 ]; then
            ## Setup a VLAN interface (if necessary)
            local IFUUID=$(uuidgen -r)
            echo "vlan add ${IFNAME} ${VLANID} ${IFUUID} ${IFMTU}" >> ${VSWITCH_CMDFILE}
            IFNAME=${IFNAME}.${VLANID}
        fi

        if [ "${DATA[0]}" == "nat" ]; then
            ## Setup a NAT translation from this address to an internal
            ## address.  The CIDR length is irrelevant but required at the CLI
            INTERNAL_ADDRESS=${DATA[1]}
            NATARGS="nat ${INTERNAL_ADDRESS}"

        elif [ "${DATA[0]}" == "snat" ]; then
            ## Mark this interface as an external gateway interface and enable
            ## SNAT on the router.   This is because AVS is optimized to only
            ## enter the SNAT code path on external interfaces.
            echo "interface set flag ${IFNAME} external" >> ${VSWITCH_CMDFILE}
            echo "router enable snat default" >> ${VSWITCH_CMDFILE}
        fi

        ## Add address to the interface
        echo "interface add addr ${IFNAME} ${IPADDR}/${LENGTH} ${NATARGS}" >> ${VSWITCH_CMDFILE}
    done

    for ROUTE in ${ROUTES[@]}; do
        DATA=(${ROUTE//,/ })
        SUBNET=${DATA[0]}
        GWIP=${DATA[1]}
        IFNAME=${DATA[2]}
        echo "route add ${SUBNET} ${IFNAME} ${GWIP} 1" >> ${VSWITCH_CMDFILE}
    done

    echo "quit" >> ${VSWITCH_CMDFILE}
    return 0
}


## Calculate the vswitch CPU list based on the CPU count
##
function get_vswitch_cpu_list()
{
    local CPU_COUNT=$1
    local CPU_LIST=""

    if [ ${CPU_COUNT} -gt 2 ]; then
        ## Limit to N-1 processors starting at 1
        CPU_LIST="1-$((CPU_COUNT-1))"
    else
        CPU_LIST="1"
    fi

    echo ${CPU_LIST}
}

## Build a vswitch engine-map string based on the CPU count
##
function get_vswitch_engine_map()
{
    local CPU_COUNT=$1
    local ENGINE_MAP=""
    local SEPARATOR=""

    for I in $(seq 1 $CPU_COUNT); do
        ENGINE_MAP="${ENGINE_MAP}${SEPARATOR}$(uuidgen -r)=${I}"
        SEPARATOR=","
    done

    echo "${ENGINE_MAP}"
}

## Build a vswitch pci-map based on the list of PCI devices and pre-generated
## UUID values
##
function get_vswitch_pci_map()
{
    local PCI_LIST=("${!1}")
    local PCI_UUIDS=("${!2}")
    local PCI_MAP=""
    local SEPARATOR=""

    for I in ${!PCI_LIST[@]}; do
        DEVICE=${PCI_LIST[$I]}
        UUID=${PCI_UUIDS[$I]}
        PCI_MAP="${PCI_MAP}${SEPARATOR}${UUID}=${DEVICE}"
        SEPARATOR=","
    done

    echo "${PCI_MAP}"
}

## Generate a list of UUID values that will later be used to map to the
## vswitch PCI device list
##
function get_vswitch_pci_uuids()
{
    local COUNT=$1
    local UUIDS=""

    for I in $(seq 1 ${COUNT}); do
        UUIDS="${UUIDS} $(uuidgen -r)"
    done

    echo ${UUIDS}
}

## Auto-detect the list of PCI devices for vswitch.  This selects the last 2 AVP
## devices in the PCI list
##
function get_vswitch_pci_devices()
{
    local DEVICE_TYPE=$1
    local DEVICE_COUNT=$2

    # split the device type into the PCI IDs
    local DEVICE=(${DEVICE_TYPE//:/ })

    echo $(pci_device_list ${DEVICE[0]} ${DEVICE[1]} ${DEVICE[2]} ${DEVICE_COUNT})
}

## Generate a mapping between port indexes and cpu indexes for vswitch engines.
##
function get_vswitch_port_map()
{
    local PCI_COUNT=$1
    local CPU_COUNT=$2
    local PCI_INDEXES=$(expand_sequence "0,$((PCI_COUNT-1))")

    if [ ${CPU_COUNT} -lt 2 ]; then
        echo "${PCI_INDEXES}:1"
    else
        local CPU_INDEXES=$(expand_sequence "1-${CPU_COUNT}")
        echo "${PCI_INDEXES}:${CPU_INDEXES}"
    fi
}

## Setup the vswitch init.d configuration file which is used to launch the vswitch
## process with the correct DPDK parameters
##
function setup_vswitch_config_file()
{
    local CPU_LIST=$(get_vswitch_cpu_list $1)
    local PCI_LIST="${!2}"

    ## Set the CPU list and master core
    sed -i -e "s#^\(VSWITCH_CPU_LIST\)=.*#\1=${CPU_LIST}#g" ${VSWITCH_CONFIG}
    sed -i -e "s#^\(VSWITCH_MASTER_CPUID\)=.*#\1=0#g" ${VSWITCH_CONFIG}

    ## Set the PCI device list
    sed -i -e "s#^\(VSWITCH_PCI_DEVICES\)=.*#\1=\"${PCI_LIST}\"#g" ${VSWITCH_CONFIG}

    ## Point vswitch to this custom commands files
    sed -i -e "s#^\(VSWITCH_CMDFILE\)=.*#\1=${VSWITCH_CMDFILE}#g" ${VSWITCH_CONFIG}

    if [ ! -z "${VSWITCH_MEM_SIZES}" ]; then
        ## Override the AVS memory settings if set
        sed -i -e "s#^\(VSWITCH_MEM_SIZES\)=.*#\1=${VSWITCH_MEM_SIZES}#g" ${VSWITCH_CONFIG}
    fi

    if [ ! -z ${VSWITCH_TEST_MODE} ]; then
        ## Enable chaining if we are trying simulate an L3 environment
        echo "VSWITCH_TEST_MODE=${VSWITCH_TESTMODE}" >> ${VSWITCH_CONFIG}
    fi
}

## Setup the vswitch ini file which is consumed directly by the vswitch process
##
function setup_vswitch_ini_file()
{
    local NUMA_COUNT=$1
    local CPU_COUNT=$2
    local PCI_LIST=("${!3}")
    local PCI_UUIDS=("${!4}")
    local ENGINE_MAP=$(get_vswitch_engine_map $((CPU_COUNT-1)))
    local PORT_MAP=$(get_vswitch_port_map ${#PCI_LIST[@]} $((CPU_COUNT-1)))
    local PCI_MAP=$(get_vswitch_pci_map PCI_LIST[@] PCI_UUIDS[@])
    local POOL_SIZE=${VSWITCH_MBUF_POOL_SIZE:-"16384"}
    local IDLE_DELAY=${VSWITCH_ENGINE_IDLE_DELAY:-"1-10000"}

    cat << EOF > ${VSWITCH_INIFILE}
[DEFAULT]
master-core=0
numa-nodes=1
mbuf-pool-size=${POOL_SIZE}
avp-guest-desc=1024
avp-host-desc=128
command-file=${VSWITCH_CMDFILE}
command-logfile=/var/log/vswitch.cmds.log
[ENGINE]
engine-map=${ENGINE_MAP}
idle-delay=${IDLE_DELAY}
port-map=${PORT_MAP}
[PCI]
device-map=${PCI_MAP}
EOF
}

function setup_vswitch()
{
    local MODE=$1
    local PCI_LIST=""
    local PCI_UUIDS=""

    if [ "x${MODE}" == "xlayer3" ]; then
        log "Setting up vswitch layer3 routing"
    else
        log "Setting up vswitch layer2 bridging on ${BRIDGE_PORTS}"
    fi

    ## Source the vswitch functions to determine the VSWITCH_PCI_DEVICES list for later.
    source /etc/vswitch/vswitch_functions.sh

    ## Auto detect CPU, NUMA, and PCI devices
    NUMA_COUNT=$(numa_count)
    CPU_COUNT=$(cpu_count)
    PCI_LIST=($(get_vswitch_pci_devices ${NIC_DEVICE:-$NIC_DEVICE_DEFAULT} \
    ${NIC_COUNT:-$NIC_COUNT_DEFAULT}))
    PCI_UUIDS=($(get_vswitch_pci_uuids ${#PCI_LIST[@]}))

    setup_vswitch_ini_file ${NUMA_COUNT} ${CPU_COUNT} PCI_LIST[@] PCI_UUIDS[@]
    setup_vswitch_config_file ${CPU_COUNT} PCI_LIST[@]

    if [ "x${MODE}" == "xlayer3" ]; then
        setup_vswitch_layer3_commands_file ADDRESSES[@] ROUTES[@] PCI_UUIDS[@]
    else
        setup_vswitch_layer2_commands_file ${BRIDGE_PORTS} ${BRIDGE_MTU} PCI_UUIDS[@]
    fi

    ## Reload the wrs-avp driver to activate the options change
    reload_wrs_avp_driver
    RET=$?
    if [ ${RET} -ne 0 ]; then
        log "Failed to re-enable AVP driver, ret=${RET}"
        return ${RET}
    fi

    ## Start services
    /etc/init.d/dpdk restart
    RET=$?
    if [ ${RET} -ne 0 ]; then
        log "Failed to start dpdk, ret=${RET}"
        return ${RET}
    fi

    /etc/init.d/vswitch restart
    RET=$?
    if [ ${RET} -ne 0 ]; then
        log "Failed to start vswitch, ret=${RET}"
        return ${RET}
    fi

    return 0
}

################################################################################
# Start Action
################################################################################
function start()
{
    log "waiting for wrs-guest-setup to finish"
    # must wait for wrs-guest-setup to avoid race conditions
    while ! systemctl show -p SubState wrs-guest-setup | grep 'exited\|dead'; do
        sleep 1
    done

    log "stopping dpdk and vswitch"
    /etc/init.d/dpdk stop
    /etc/init.d/vswitch stop

    log "loading configurations"
    source /etc/init.d/tis_automation_init.config

    FUNCTIONS=(${FUNCTIONS//,/ })
    for FUNCTION in ${FUNCTIONS[@]}; do
        case ${FUNCTION} in
            "vswitch")
                setup_vswitch "layer2"
                RET=$?
                ;;
            "avr")
                setup_vswitch "layer3"
                RET=$?
                ;;
            "routing")
                setup_kernel_routing
                RET=$?
                ;;
            *)
                log "Unknown function '${FUNCTION}'; ignoring"
                RET=0
        esac
        if [ ${RET} -ne 0 ]; then
            log "Failed to setup function '${FUNCTION}'; stopping"
            return ${RET}
        fi
    done
    return 0
}

################################################################################
# Stop Action
################################################################################
function stop()
{
    return 0
}

################################################################################
# Status Action
################################################################################
function status()
{
    return 0
}

################################################################################
# Main Entry
################################################################################

case "$1" in
  start)
        start
        ;;
  stop)
        stop
        ;;
  restart)
        stop
        start
        ;;
  status)
        status
        ;;
  *)
        echo $"Usage: $0 {start|stop|restart|status}"
        exit 1
esac

exit 0
