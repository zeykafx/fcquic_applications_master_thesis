from dataclasses import dataclass, field
from .pim import *
from .isis import *
from .ip import *
from .bfd import *
from ipaddress import IPv4Address, IPv4Network


@dataclass
class GlobalConf:
    pim: PimGlobal = field(default_factory=PimGlobal)
    isis: IsisGlobal = field(default_factory=IsisGlobal)
    ip: IpGlobal = field(default_factory=IpGlobal)
    bfd: BfdGlobal = field(default_factory=BfdGlobal)

    def __str__(self):
        s = ""
        for field in [self.ip, self.pim, self.isis, self.bfd]:
            conf = str(field)
            if conf != "":
                s += conf
                s += "\n"
        return s


@dataclass
class InterfaceConf:
    pim: PimInterface = field(default_factory=PimInterface)
    isis: IsisInterface = field(default_factory=IsisInterface)
    ip: IpInterface = field(default_factory=IpInterface)

    def __str__(self):
        s = ""
        for field in [self.pim, self.isis, self.ip]:
            conf = str(field)
            if conf != "":
                s += conf
        return s


@dataclass
class FRRouting:
    glb: GlobalConf = field(default_factory=GlobalConf)
    interfaces: dict[str, InterfaceConf] = field(default_factory=dict)

    def __str__(self):
        s = f"{str(self.glb)}\n"
        for interface, conf in self.interfaces.items():
            s += f"interface {interface}\n"
            s += str(conf)
            s += "exit\n"
        return s

    def add_interface(self, interface):
        self.interfaces[interface] = InterfaceConf()

    def get_interface(self, interface):
        return self.interfaces[interface]


if __name__ == "__main__":
    conf = FRRouting()
    conf.glb.pim.set_ssm_range(IPv4Network("224.0.0.0/24"))

    conf.add_interface("eth0")
    eth0_conf = conf.get_interface("eth0")
    eth0_conf.pim.enable()
    eth0_conf.ip.set_addr(IPv4Address("10.0.0.1"))

    print(conf)
