import os


class TisInitServiceScript(object):
    script_path = "/etc/init.d/tis_automation_init.sh"
    configuration_path = "/etc/init.d/tis_automation_init.config"
    service_name = "tis_automation_init.service"
    service_path = "/etc/systemd/system/{}".format(service_name)
    service = """
[Unit]
Description=TiS Automation Initialization
After=NetworkManager.service network.service wrs-guest-setup.service

[Service]
Type=simple
RemainAfterExit=yes
ExecStart=/bin/bash {} start
ExecStop=/bin/bash {} stop

[Install]
WantedBy=multi-user.target
""".format(script_path, script_path)

    @classmethod
    def configure(cls, vm_ssh, **kwargs):
        cfg = "\n".join(["{}={}".format(*kv) for kv in kwargs.items()])
        vm_ssh.exec_sudo_cmd(
            "cat > {} << 'EOT'\n{}\nEOT".format(cls.configuration_path, cfg),
            fail_ok=False)
        vm_ssh.exec_sudo_cmd(
            "cat > %s << 'EOT'\n%s\nEOT" % (cls.service_path, cls.service),
            fail_ok=False)

    @classmethod
    def enable(cls, vm_ssh):
        vm_ssh.exec_sudo_cmd(
            "systemctl daemon-reload", fail_ok=False)
        vm_ssh.exec_sudo_cmd(
            "systemctl enable %s" % cls.service_name, fail_ok=False)

    @classmethod
    def start(cls, vm_ssh):
        vm_ssh.exec_sudo_cmd(
            "systemctl daemon-reload", fail_ok=False)
        vm_ssh.exec_sudo_cmd(
            "systemctl start %s" % cls.service_name, fail_ok=False)

    @classmethod
    def src(cls):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "tis_automation_init.sh")

    @classmethod
    def dst(cls):
        return cls.script_path


class KPktgen(object):
    script_path = "/root/kpktgen.sh"
    configuration_path = "/root/kpktgen.config"

    @classmethod
    def src(cls):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "kpktgen.sh")

    @classmethod
    def dst(cls):
        return cls.script_path

    @classmethod
    def configure(cls, vm_ssh, **kwargs):
        cfg = "\n".join(["{}={}".format(*kv) for kv in kwargs.items()])
        vm_ssh.exec_sudo_cmd(
            "cat > {} << 'EOT'\n{}\nEOT".format(cls.configuration_path, cfg),
            fail_ok=False)

    @classmethod
    def start(cls, vm_ssh):
        vm_ssh.exec_sudo_cmd("nohup bash {} &>/dev/null &".format(
            cls.script_path))


class DPDKPktgen(object):
    script_path = "/root/dpdk_pktgen.sh"
    configuration_path = "/root/dpdk_pktgen.config"

    @classmethod
    def src(cls):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "dpdk_pktgen.sh")

    @classmethod
    def dst(cls):
        return cls.script_path

    @classmethod
    def configure(cls, vm_ssh, *cmds):
        cfg = "\n".join(cmds)
        vm_ssh.exec_sudo_cmd(
            "cat > {} << 'EOT'\n{}\nEOT".format(cls.configuration_path, cfg),
            fail_ok=False)

    @classmethod
    def start(cls, vm_ssh):
        # dpdk pktgen REQUIRES a tty (fails during initialization otherwise)
        # echo-ing 'quit' will not work, use 'kill' with 'ps aux | grep nohup'
        # to terminate
        vm_ssh.exec_sudo_cmd(
            "nohup socat EXEC:{},pty PTY,link=pktgen.pty,echo=0,icanon=0 "
            "&>/dev/null &".format(cls.script_path))
