from ipaddress import IPv4Network

class IpGlobal:
    def __init__(self):
        self.forwarding = False

    def forward(self):
        self.forwarding = True

    def __str__(self):
        s = ""
        if self.forwarding:
            s += F"ip forwarding"
        return s

class IpInterface:
    def __init__(self):
        self.addr = None

    def set_addr(self, addr: IPv4Network):
        self.addr = addr

    def __str__(self):
        s = ""
        if self.addr is not None:
            s += F"  ip address {self.addr}\n"
        return s
