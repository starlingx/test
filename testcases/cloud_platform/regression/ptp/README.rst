==============================================
Precision Time Protocol (PTP) Test Automation
==============================================

Overview
========

This directory contains automated tests for the Precision Time Protocol (PTP) functionality in StarlingX. These tests validate that time synchronization works correctly across the cloud platform.

What is PTP?
-----------

PTP (Precision Time Protocol, IEEE 1588) is a protocol used to synchronize clocks throughout a computer network. Unlike NTP (Network Time Protocol) which typically provides millisecond accuracy, PTP achieves clock accuracy in the sub-microsecond (less than one millionth of a second) range, making it essential for telecommunications, industrial automation, and financial trading systems.

**Why PTP is Important for StarlingX:**
PTP enables critical timing-sensitive applications in telecommunications by ensuring all network devices operate with the same precise time reference. This is essential for:

- 5G network synchronization
- Radio access network (RAN) timing
- Mobile backhaul synchronization
- Industrial automation
- Financial transaction timestamping

**How PTP Works:**
1. Special hardware in network cards creates timestamps when packets are sent and received
2. These timestamps are used to calculate network delay and clock offset
3. Slave clocks adjust their time based on these calculations
4. The system continuously monitors and adjusts to maintain synchronization

**Key PTP Concepts:**

- **Grandmaster Clock**: The primary reference clock that provides time to the network. Usually synchronized to GPS/GNSS or another highly accurate external source.

- **Boundary Clock (BC)**: A clock with multiple network connections that can synchronize to a master and serve as a time source for other clocks. Acts as both a slave (to upstream) and master (to downstream).

- **Transparent Clock (TC)**: A device that measures packet delay as it passes through and adds this information to help improve accuracy.

- **Ordinary Clock (OC)**: A clock with a single network connection, acting as either master or slave.

- **Time Slave Clock**: A clock that synchronizes to a master but doesn't provide time to other devices.

- **GNSS**: Global Navigation Satellite System provides an external time reference (like GPS, GLONASS, Galileo). Provides extremely accurate time derived from atomic clocks in satellites.

- **Holdover**: Operation mode when external reference is lost but clock continues based on previous synchronization. Quality of holdover depends on the stability of local oscillators.

- **PPS (Pulse Per Second)**: A precise electrical signal that pulses exactly once per second, used to synchronize hardware clocks.

- **Hardware Timestamping**: Special hardware in network cards that timestamps packets at the physical layer for greater accuracy.

Test Environment Setup
=====================

Physical Topology
---------------

The test environment is based on the configuration in ``ptp_data_westport_dx_plus_tgm_tbc.json5``. This topology represents a real-world PTP deployment with precise timing requirements.

**Network and Time Flow Diagram:**

::

    +----------------+                 +----------------+
    |                |                 |                |
    |   GNSS Source  |                 |  SMA Clock     |
    | (GPS Satellite)|                 | (External Ref) |
    +-------+--------+                 +-------+--------+
            |                                  |
            | PPS Signal                       | Clock Signal
            | (1 pulse per second)             | (10MHz reference)
            v                                  v
    +-------+--------+                 +-------+--------+
    |                |                 |                |
    | Controller-0   |                 | Controller-0   |
    | NIC1 (TGM)     +---------------->+ NIC2 (TGM)     |
    | enp81s0f2      | Internal Sync   | enp138s0f1     |
    +-------+--------+                 +-------+--------+
            |                                  |
            | PTP Master                       | PTP Master
            | (Priority 100)                   | (Priority 100)
            v                                  v
    +-------+--------+                 +-------+--------+
    |                |                 |                |
    | Controller-1   |                 | Controller-1   |
    | NIC1 (TBC)     |                 | NIC2 (TBC)     |
    | enp81s0f1      |                 | enp138s0f0     |
    +-------+--------+                 +-------+--------+
            |                                  |
            | PTP Master                       | PTP Master
            | (Priority 110)                   | (Priority 110)
            v                                  v
    +-------+--------+                 +-------+--------+
    |                |                 |                |
    | Compute-0      |                 | Compute-0      |
    | NIC1           |                 | NIC2           |
    | enp81s0f2      |                 | enp138s0f0     |
    +----------------+                 +----------------+

**Key Components Explained:**

1. **Time Sources**:
   - **GNSS Source**: Provides accurate time from GPS/GNSS satellites to Controller-0 NIC1
   - **SMA Clock**: External reference clock connected to Controller-0 NIC2 via SMA connector

2. **PTP Instances and Roles**:
   - **ptp1**: Running on Controller-0 NIC1 (enp81s0f2) - Telecom Grandmaster (TGM)
   - **ptp2**: Running on Controller-1 NIC1 (enp81s0f1) - Time Boundary Clock (TBC)
   - **ptp3**: Running on Controller-0 NIC2 (enp138s0f1) - Telecom Grandmaster (TGM)
   - **ptp4**: Running on Controller-1 NIC2 (enp138s0f0) - Time Boundary Clock (TBC)

3. **Time Flow**:
   - GNSS → Controller-0 NIC1 → Controller-1 NIC1 → Compute-0 NIC1
   - SMA Clock → Controller-0 NIC2 → Controller-1 NIC2 → Compute-0 NIC2

4. **Priority Settings**:
   - Controller-0 instances: Priority 100 (higher precedence)
   - Controller-1 instances: Priority 110 (lower precedence)

5. **Physical Connections**:
   - All connections between controllers and compute nodes use standard network cables
   - GNSS connection uses RF cable to antenna
   - SMA connections use specialized timing cables

Hardware Requirements
-------------------

- **Controllers and Compute Nodes**: StarlingX standard deployment
- **NICs**: Intel E810 series or compatible with hardware timestamping
- **GNSS Receiver**: GPS/GNSS receiver with PPS output
- **SMA Connections**: For clock signal distribution
- **BeagleBone Black**: For GNSS power control (lab environment only)

Software Configuration
--------------------

The PTP configuration is defined in JSON5 files:

- **ptp_data_westport_dx_plus_tgm_tbc.json5**: Defines expected PTP configuration
- **default.json5**: Contains interface mappings and hardware details

Service types in the configuration:
- **TGM**: Telecom Grandmaster - Primary time source (Controller-0)
- **TBC**: Time Boundary Clock - Distributes time (Controller-1)
- **T-TSC**: Telecom Time Slave Clock - Receives time only

Running the Tests
================

Prerequisites
-----------

1. Ensure all hardware is properly connected according to the topology
2. Verify GNSS antenna has clear sky view
3. Confirm all nodes are up and running
4. PTP services should be configured but not necessarily synchronized

Common Alarms
============

- **100.119**: PTP-related alarms including:
  - "not locked to remote PTP Grand Master"
  - "GNSS signal loss state: holdover"
  - "1PPS signal loss state: holdover"
  - "PTP clocking is out of tolerance"

Alarm severity levels:
- **Major**: Service affecting issues (GNSS signal loss, no lock to master)
- **Minor**: Non-service affecting issues (out of tolerance)

Troubleshooting
==============

Common Issues and Solutions
-------------------------

1. **GNSS Signal Loss** (Error: "GNSS signal loss state: invalid")

   **Symptoms:**
   - Major alarm 100.119 with message "GNSS signal loss state: invalid"
   - PTP instances enter holdover mode
   - Clock class changes from 6 to 248

   **Solutions:**
   - **Check physical setup:**
     - Ensure GNSS antenna has clear view of the sky (ideally outdoors or near window)
     - Verify antenna cable is properly connected to the GNSS receiver
     - Check if antenna has power (active antennas require power)
   
   - **Verify GNSS power control:**
     - Run `./yow2-beagleboneblack-xxx.exp <gpio_port> on` to power on GNSS
     - Check if BeagleBone Black is properly connected and powered
   
   - **Improve signal detection:**
     - Add `ts2phc.extts_polarity=both` parameter to ts2phc configuration
     - This allows detection of both rising and falling edges of PPS signal
     - Restart ts2phc service after configuration change

2. **PTP Not Synchronizing** (Error: "not locked to remote PTP Grand Master")

   **Symptoms:**
   - Major alarm 100.119 with message "not locked to remote PTP Grand Master"
   - Port state shows as "LISTENING" or "FAULTY" instead of "MASTER" or "SLAVE"
   - PMC commands show incorrect parent data

   **Solutions:**
   - **Check network connectivity:**
     - Verify network cables are properly connected between all nodes
     - Run `ping` tests between controllers and compute nodes
     - Check for network errors with `ethtool -S <interface>`
   
   - **Verify PTP configuration:**
     - Ensure interface mappings in JSON5 file match actual hardware
     - Check that all required PTP instances are running with `systemctl status ptp4l@*`
     - Verify domain numbers match across all instances
   
   - **Hardware timestamping:**
     - Confirm hardware timestamping is enabled: `ethtool -T <interface>`
     - Verify PTP hardware clock exists: `ls /dev/ptp*`
     - Check driver support: `dmesg | grep ptp`

3. **Out of Tolerance Alarms** (Error: "PTP clocking is out of tolerance")

   **Symptoms:**
   - Minor alarm 100.119 with message "PTP clocking is out of tolerance by X microsecs"
   - System continues to operate but with degraded timing accuracy
   - Large offset values in PTP statistics

   **Solutions:**
   - **Check for network issues:**
     - Look for network congestion or packet loss
     - Verify QoS settings prioritize PTP traffic
     - Check for sources of jitter in the network
   
   - **Verify hardware connections:**
     - Ensure SMA connections are secure and properly terminated
     - Check for signal integrity issues with oscilloscope if available
     - Verify cable quality and length (shorter is better)
   
   - **Configuration tuning:**
     - Adjust `tx_timestamp_timeout` parameter if needed
     - Consider increasing `logSyncInterval` for more frequent synchronization
     - Check for proper delay mechanism configuration

Diagnostic Commands and Interpretation
================================

Below are essential commands for diagnosing PTP issues, along with explanations of what to look for in the output:

.. code-block:: bash

    # Check PTP daemon status for specific instance
    systemctl status ptp4l@ptp1
    # Look for: "Active: active (running)" and no error messages

    # View PTP logs for detailed synchronization information
    cat /var/log/ptp4l.log
    # Look for: "selected best master" messages and offset values
    # Good offset values should be in nanoseconds, not microseconds

    # Check GNSS status through CGU (Clock Generation Unit)
    cat /sys/kernel/debug/ice/<pci_address>/cgu
    # Look for: 
    # - "GNSS-1PPS state: valid" (good) or "invalid" (problem)
    # - "EEC DPLL status: locked_ho_acq" (good) or "holdover" (problem)
    # - "PPS DPLL status: locked_ho_acq" (good) or "holdover" (problem)

    # Find PCI address for your NIC
    grep PCI_SLOT_NAME /sys/class/net/enp81s0f2/device/uevent
    # Example output: PCI_SLOT_NAME=0000:81:00.2

    # View current PTP configuration and status
    pmc -u -b 0 'GET CURRENT_DATA_SET'
    # Look for: "offsetFromMaster" (should be small, <100ns is excellent)
    
    pmc -u -b 0 'GET PARENT_DATA_SET'
    # Look for: "parentPortIdentity" (shows which clock you're synchronized to)
    
    pmc -u -b 0 'GET TIME_PROPERTIES_DATA_SET'
    # Look for: "timeSource" (should be 0x20 for GNSS or 0x60 for PTP)
    
    pmc -u -b 0 'GET GRANDMASTER_SETTINGS_NP'
    # Look for: "clockClass" (6=synchronized to GNSS, 248=holdover)

    # Check for PTP alarms
    fm alarm-list | grep ptp
    # Common alarm IDs: 100.119 (PTP-related alarms)
    
    # Check hardware timestamping capability
    ethtool -T enp81s0f2
    # Look for: "hardware-transmit" and "hardware-receive" capabilities
    
    # Monitor PTP synchronization in real-time
    watch -n 1 "pmc -u -b 0 'GET CURRENT_DATA_SET' | grep offsetFromMaster"
    # Values should be stable and small (nanoseconds range)
    
    # Check if ts2phc is properly detecting GNSS signal
    journalctl -u ts2phc@ts1 -f
    # Look for: "extts" events occurring once per second

**Understanding Clock Class Values:**

- **6**: Synchronized to primary reference (GNSS) - Highest accuracy
- **7**: Synchronized to primary reference but in holdover - Starting to drift
- **13-14**: Synchronized to application-specific source - Alternative reference
- **52**: Degraded reference but synchronized - Reduced accuracy
- **165**: Clock in holdover mode after losing synchronization - Drifting
- **187**: In holdover but within specifications - Warning
- **193**: In holdover, out of specifications - Problem
- **248**: Default/uncalibrated clock - Worst quality, complete loss
- **255**: Slave-only clock - Receives time, never provides it

**Clock Accuracy Values:**
- **0x20**: "±25 nanoseconds - Highest accuracy with GNSS lock",
- **0x21**: "±100 nanoseconds - Very high accuracy",
- **0x22**: "±250 nanoseconds - High accuracy",
- **0xFE**: "Unknown - Accuracy cannot be determined (typically in holdover)",
- **0xFF**: "Reserved/Invalid - Not used for synchronization"

**Port States:**
- **MASTER**: "Port provides timing to downstream devices",
- **SLAVE**: "Port receives timing from an upstream master",
- **PASSIVE**: "Port is not currently used for synchronization",
- **LISTENING**: "Port is monitoring the network but not synchronized",
- **FAULTY**: "Port has detected a fault condition",
- **DISABLED**: "Port is administratively disabled",
- **UNCALIBRATED**: "Port is in the process of calibrating",
- **PRE_MASTER**: "Port is transitioning to MASTER state"
}

** Flag Values:**
- **time_traceable_1**: "Time is traceable to a primary reference (GNSS/UTC)",
- **time_traceable_0**: "Time is not traceable to a primary reference",
- **frequency_traceable_1**: "Frequency is traceable to a primary reference",
- **frequency_traceable_0**: "Frequency is not traceable to a primary reference",
- **current_utc_offset_valid_1**: "The UTC offset is valid and can be trusted",
- **current_utc_offset_valid_0**: "The UTC offset is not valid and cannot be trusted"

## Clock Accuracy Values

| Accuracy Value | Description | Meaning in Tests |
|----------------|-------------|------------------|
| 0x20 | ±25 nanoseconds | Highest accuracy, typically with GNSS lock |
| 0x21 | ±100 nanoseconds | Very high accuracy |
| 0x22 | ±250 nanoseconds | High accuracy |
| 0xFE | Unknown | Accuracy cannot be determined (typically in holdover) |
| 0xFF | Reserved/Invalid | Not used for synchronization |

## Port States

| Port State | Description | Test Implications |
|------------|-------------|-------------------|
| MASTER | Port provides timing to downstream devices | Device is acting as time source |
| SLAVE | Port receives timing from an upstream master | Device is synchronizing to another clock |
| PASSIVE | Port is not currently used for synchronization | Monitoring only, not active in timing path |
| LISTENING | Port is monitoring the network but not synchronized | Initial state or recovering from error |
| FAULTY | Port has detected a fault condition | Problem with timing or physical connection |
| DISABLED | Port is administratively disabled | Not participating in PTP |
| UNCALIBRATED | Port is in the process of calibrating | Transitional state during initialization |
| PRE_MASTER | Port is transitioning to MASTER state | Temporary state before becoming MASTER |


References and Learning Resources
================================

Standards and Specifications
--------------------------

- **IEEE 1588-2008 Standard**: The official PTP version 2 specification
  https://standards.ieee.org/ieee/1588/4355/

- **ITU-T G.8275.1**: Precision time protocol telecom profile for phase/time synchronization
  https://www.itu.int/rec/T-REC-G.8275.1/en

- **ITU-T G.8272**: Timing characteristics of primary reference time clocks
  https://www.itu.int/rec/T-REC-G.8272/en

StarlingX Documentation
---------------------

- **StarlingX PTP Configuration Guide**:
  https://docs.starlingx.io/operations/ptp.html

- **StarlingX System Configuration Guide**:
  https://docs.starlingx.io/configuration/index-config-e244b.html

Software Documentation
-------------------

- **linuxptp Documentation**:
  https://linuxptp.sourceforge.net/

- **PTP Hardware Clock Driver Documentation**:
  https://www.kernel.org/doc/html/latest/driver-api/ptp.html

- **Intel E810 NIC Documentation**:
  https://www.intel.com/content/www/us/en/products/details/ethernet/800-network-adapters.html

Learning Resources
---------------

- **Introduction to PTP** (Video):
  https://www.youtube.com/watch?v=OEJPiHNl3hw

- **PTP in Telecommunications Networks** (White Paper):
  https://www.microsemi.com/document-portal/doc_view/133268-precision-time-protocol-ptp-in-mobile-backhaul

- **Troubleshooting PTP** (Tutorial):
  https://blog.meinbergglobal.com/2019/02/28/troubleshooting-ptp/

- **GNSS and PTP Integration** (Article):
  https://www.orolia.com/resources/blog/gnss-and-ptp-perfect-partners-for-resilient-timing/

Related Test Files
---------------

- **test_ptp.py**: Main test file for PTP functionality
- **ptp_data_westport_dx_plus_tgm_tbc.json5**: PTP configuration file
- **default.json5**: Interface mappings and hardware details