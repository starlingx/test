============================
**resources/** Documentation
============================

The **resources/** directory contains various test-related assets used within the StarlingX Test Framework,
including containerized applications, custom-built Docker images, nightly regression configurations 
(deployment files, pod definitions, and Network Attachment Definitions (NADs)), and sanity test pods / configs.

--------
Contents
--------

.. toctree::
   :maxdepth: 1

   resources_overview

Directory Structure
=======================

Below is an overview of the **resources/** directory structure.  
This highlights key directories and files but does not include every file:

.. code-block:: bash

   resources/
   ├── cloud_platform
   │   ├── containers
   │   │   ├── hello-kitty_armada.tgz
   │   │   ├── hello-kitty-min-k8s-version.tgz
   │   ├── images
   │   │   └── node-hello-alpine
   │   │       ├── Dockerfile
   │   │       ├── node-hello-alpine.tar.gz
   │   │       └── server.js
   │   ├── nightly_regression
   │   │   ├── calicoctl_crb.yaml
   │   │   └── daemon_set_daemonset_ipv4.yaml
   │   ├── sanity
   │       └── pods
   │           ├── client-pod1.yaml
   │           └── server_pod.yaml
   ├── images
       ├── busybox.tar
       └── calico-ctl.tar
