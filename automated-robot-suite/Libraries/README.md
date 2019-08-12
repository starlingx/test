# Table of contents

- [iso_setup python module](#iso_setup-python-module)

# iso_setup python module

The iso_setup.py in this folder provides the capability to setup a StarlingX
iso with specific configuration, this configuration comes from the `config.ini`
file.

The **config.ini** file in the section `iso_installer` contains the
variable `KERNEL_OPTION` which can have the following values.


| Value | Description                                                  |
| ----- | ------------------------------------------------------------ |
| 0     | Standard Controller Configuration > Serial Console > Standard Security Boot Profile |
| S0    | Standard Controller Configuration > Serial Console > Extended Security Boot Profile |
| 1     | Standard Controller Configuration > Graphical Console > Standard Security Boot Profile |
| S1    | Standard Controller Configuration > Graphical Console > Extended Security Boot Profile |
| 2     | All-in-one Controller Configuration > Serial Console > Standard Security Boot Profile |
| S2    | All-in-one Controller Configuration > Serial Console > Extended Security Boot Profile |
| 3     | All-in-one Controller Configuration > Graphical Console > Standard Security Boot Profile |
| S3    | All-in-one Controller Configuration > Graphical Console > Extended Security Boot Profile |
| 4     | All-in-one (lowlatency) Controller Configuration >  Serial Console > Standard Security Boot Profile |
| S4    | All-in-one (lowlatency) Controller Configuration >  Serial Console > Extended Security Boot Profile |
| 5     | All-in-one (lowlatency) Controller Configuration >  Graphical Console > Standard Security Boot Profile |
| S5    | All-in-one (lowlatency) Controller Configuration >  Graphical Console > Extended Security Boot Profile |

