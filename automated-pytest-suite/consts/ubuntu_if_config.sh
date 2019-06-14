#!/bin/bash

# Ubuntu cloud-init user data script to be executed after ubuntu vm
# initialization

sudo echo -e "auto eth1\niface eth1 inet dhcp\n\nauto eth2\niface eth2 inet dhcp" >> "/etc/network/interfaces"
sudo ifup eth1
sudo ifup eth2

ip addr