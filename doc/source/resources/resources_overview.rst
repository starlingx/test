.. _resources-overview:

=======================
Resources Overview
=======================

The **resources/** directory contains various test-related assets used within the StarlingX Test Framework,
including containerized applications, custom-built Docker images, nightly regression configurations 
(deployment files, pod definitions, and Network Attachment Definitions (NADs)), and sanity test pods / configs.

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

resources/cloud_platform/containers
-----------------------------------

Contains **packaged containerized applications** in Helm and FluxCD formats for Kubernetes-based testing.

**Example files:**  

- ``hello-kitty.tgz`` (FluxCD deployment package with Helm charts)  
- ``hello-kitty_armada.tgz`` (Armada manifest for Helm-based Kubernetes deployments)  
- ``hello-kitty-min-k8s-version.tgz`` (Minimal Helm chart version with Kubernetes version constraints, including FluxCD manifests)  
- ``hello-kitty_no_secret.tgz`` (Variant of `hello-kitty` with no secrets in the deployment)  

resources/cloud_platform/images
--------------------------------

Contains **custom-built container images** for cloud platform validation.

- ``node-hello-alpine/`` (Directory containing the Docker build context for a Node.js application)  

  - ``node-hello-alpine.tar.gz`` (Pre-built Docker image for the Node.js application)  
  - ``Dockerfile`` (Defines how to build the `node-hello-alpine` Docker image)  
  - ``server.js`` (Node.js application file that runs inside the container)  

resources/cloud_platform/nightly_regression
-------------------------------------------

Contains **YAML configuration files** used for nightly regression testing.

**Example files:**

- ``calicoctl_crb.yaml`` (Calico ClusterRoleBinding configuration)  
- ``calicoctl_cr.yaml`` (Calico ClusterRole configuration)  
- ``daemon_set_daemonset_ipv4.yaml`` (DaemonSet definition for IPv4 testing)  
- ``netdef_test-sriovdp_ipv4_with_pools.yaml`` (Network definition for SR-IOV device plugin with IPv4 pools)  

resources/cloud_platform/sanity/pods
-------------------------------------

Contains **sanity test pod definitions** used for basic Kubernetes validation.

**Example files:**

- ``client-pod1.yaml`` (Kubernetes client pod configuration)  
- ``consumer_app.yaml`` (Pod definition for a consumer application in sanity testing)  
- ``server_pod.yaml`` (Server pod used for network testing)  

resources/images
-----------------

Contains **general-purpose Docker images** used across multiple test cases.

**Example files:**  

- ``busybox.tar`` (Docker image)  
- ``pv-test.tar`` (Docker image)  
- ``calico-ctl.tar`` (Docker image)  
- ``resource-consumer.tar`` (Docker image)  

Key Takeaways
=======================

- ``resources/cloud_platform/containers`` → **Packaged Kubernetes applications** (Helm charts, FluxCD deployments)  
- ``resources/cloud_platform/images`` → **Custom-built Docker images** for cloud platform testing  
- ``resources/cloud_platform/nightly_regression`` → **Nightly regression test configurations** (Calico, DaemonSets, Network definitions, etc.)  
- ``resources/cloud_platform/sanity/pods`` → **Sanity test pod configurations** for Kubernetes validation  
- ``resources/images`` → **General-purpose container images** for various automation tests  

This structure ensures clarity, modularity, and efficient resource management within the StarlingX test framework.
