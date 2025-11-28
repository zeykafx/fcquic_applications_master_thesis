from ipaddress import IPv4Network

class PimGlobal:
    def __init__(self):
        self.ssm_range = None
        self.use_asm = False
        self.rp_priority = None
        self.asm_prefix = None

    def set_use_asm(self, use_asm: bool):
        self.use_asm = use_asm

    def set_asm_prefix(self, prefix: IPv4Network):
        self.asm_prefix = prefix

    def set_rp_priority(self, priority: int):
        self.rp_priority = priority

    def set_ssm_range(self, range: IPv4Network):
        self.ssm_range = range

    def __str__(self):
        s = ""
        if self.ssm_range is not None:
            s += f"ip prefix-list multicast permit {self.ssm_range}\n"

        if self.ssm_range is not None or self.use_asm:
            s += "router pim\n"
            if self.use_asm:
                s += f"  bsr candidate-rp priority {self.rp_priority}\n"
                s += f"  bsr candidate-bsr priority {self.rp_priority}\n"
                s += f"  bsr candidate-rp group {self.asm_prefix}\n"
            else:
                s += "  ssm prefix-list multicast\n"
            s += "exit"

        return s


class PimInterface:
    def __init__(self):
        self.enabled = False

    def enable(self):
        self.enabled = True

    def __str__(self):
        s = ""
        if self.enabled:
            s += "  ip router pim\n"
            s += "  ip pim sm\n"
            s += "  ip igmp\n"
            s += "  ip igmp immediate-leave\n"
        return s
