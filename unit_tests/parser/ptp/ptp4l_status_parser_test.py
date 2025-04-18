from keywords.ptp.ptp4l.objects.ptp4l_status_output import PTP4LStatusOutput

ptp4l_status_output = [
    '● ptp4l@ptp1.service - Precision Time Protocol (PTP) service\n',
    'Loaded: loaded (/etc/systemd/system/ptp4l@.service; enabled; vendor preset: disabled)\n',
    'Active: active (running) since Mon 2025-02-10 18:36:34 UTC; 3 days ago\n',
    'Main PID: 15221 (ptp4l)\n',
    'Tasks: 1 (limit: 150897)\n',
    'Memory: 336.0K\n',
    'CPU: 1min 33.917s\n',
    'CGroup: /system.slice/system-ptp4l.slice/ptp4l@ptp1.service\n',
    '└─15221 /usr/sbin/ptp4l -f /etc/linuxptp/ptpinstance/ptp4l-ptp1.conf\n',
    '\n',
    '● ptp4l@ptp3.service - Precision Time Protocol (PTP) service\n',
    'Loaded: loaded (/etc/systemd/system/ptp4l@.service; enabled; vendor preset: disabled)\n',
    'Active: active (running) since Wed 2025-02-12 16:22:23 UTC; 2 days ago\n',
    'Process: 3816049 ExecStartPost=/bin/bash -c echo $MAINPID > /var/run/ptp4l-ptp3.pid (code=exited, status=0/SUCCESS)\n',
    'Main PID: 3816048 (ptp4l)\n',
    'Tasks: 1 (limit: 150897)\n',
    'Memory: 328.0K\n',
    'CPU: 38.984s\n',
    'CGroup: /system.slice/system-ptp4l.slice/ptp4l@ptp3.service\n',
    '└─3816048 /usr/sbin/ptp4l -f /etc/linuxptp/ptpinstance/ptp4l-ptp3.conf\n',
]


def test_ptp4l_service_status_output_parser():
    """
        Tests ptp4l_status_output parser
        Returns:

        """
    ptp4l_service_status_output = PTP4LStatusOutput(ptp4l_status_output)

    # validate first service 'ptp1.service'
    ptp4l_status_object = ptp4l_service_status_output.get_ptp4l_object('ptp1')

    assert ptp4l_status_object.get_active() == 'active (running) since Mon 2025-02-10 18:36:34 UTC; 3 days ago'
    assert ptp4l_status_object.get_c_group() == '/system.slice/system-ptp4l.slice/ptp4l@ptp1.service'
    assert ptp4l_status_object.get_command() == '15221 /usr/sbin/ptp4l -f /etc/linuxptp/ptpinstance/ptp4l-ptp1.conf'
    assert ptp4l_status_object.get_cpu() == '1min 33.917s'
    assert ptp4l_status_object.get_loaded() == 'loaded (/etc/systemd/system/ptp4l@.service; enabled; vendor preset: disabled)'
    assert ptp4l_status_object.get_main_pid() == '15221 (ptp4l)'
    assert ptp4l_status_object.get_memory() == '336.0K'
    assert ptp4l_status_object.get_process() == ''
    assert ptp4l_status_object.get_tasks() == '1 (limit: 150897)'

    # validate second service 'ptp3.service
    ptp4l_status_object = ptp4l_service_status_output.get_ptp4l_object('ptp3')

    assert ptp4l_status_object.get_active() == 'active (running) since Wed 2025-02-12 16:22:23 UTC; 2 days ago'
    assert ptp4l_status_object.get_c_group() == '/system.slice/system-ptp4l.slice/ptp4l@ptp3.service'
    assert ptp4l_status_object.get_command() == '3816048 /usr/sbin/ptp4l -f /etc/linuxptp/ptpinstance/ptp4l-ptp3.conf'
    assert ptp4l_status_object.get_cpu() == '38.984s'
    assert ptp4l_status_object.get_loaded() == 'loaded (/etc/systemd/system/ptp4l@.service; enabled; vendor preset: disabled)'
    assert ptp4l_status_object.get_main_pid() == '3816048 (ptp4l)'
    assert ptp4l_status_object.get_memory() == '328.0K'
    assert ptp4l_status_object.get_process() == '3816049 ExecStartPost=/bin/bash -c echo $MAINPID > /var/run/ptp4l-ptp3.pid (code=exited, status=0/SUCCESS)'
    assert ptp4l_status_object.get_tasks() == '1 (limit: 150897)'
