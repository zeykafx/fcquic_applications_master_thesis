from topo import Topology
from ipaddress import IPv4Network
import argparse
from math import ceil


bandwidth_source="30Mbit"
bandwidth_high="12.5Mbit"
bandwidth_medium="6.5Mbit"
bandwidth_low="3.5Mbit"
delay="1ms"
buffer=250

def str_bw(bw):
    if bw == bandwidth_medium :
        return "Medium"
    elif bw == bandwidth_low:
        return "Low"
    else:
        return "High"

def get_bw(client: int, n: int):
    if client <= n / 2:
        return (bandwidth_medium, bandwidth_low)
    else:
        return (bandwidth_high, bandwidth_medium)


def set_link_properties(topo: Topology, node1: str, node2: str, bw: str, delay: str, buffer: int, codel: bool = False):
    topo.set_bw(node1, node2, bw)
    topo.set_delay(node1, node2, delay)
    topo.set_limit(node1, node2, buffer)
    topo.enable_codel(node1, node2, codel)

if __name__ == "__main__":
    parser = argparse.ArgumentParser("topo")
    parser.add_argument("mode", choices=["setup", "teardown"])
    parser.add_argument("-s", "--sources", type=int, default=1)
    parser.add_argument("-r", "--receivers", type=int, default=2)
    args = parser.parse_args()

    sources=args.sources
    receivers=args.receivers
    codel=False

    topo = Topology()

    router1="router1"
    router2="router2"
    router3="router3"
    routers = [router1, router2, router3]

    for router in routers:
        topo.add_node(router, router=True)

    topo.add_link(router1, router2, IPv4Network(F"10.2.0.0/24"))
    set_link_properties(topo, router1, router2, bandwidth_source, delay, buffer, codel)
    topo.add_link(router1, router3, IPv4Network(F"10.3.0.0/24"))
    set_link_properties(topo, router1, router3, bandwidth_source, delay, buffer, codel)

    for i in range(1, sources + 1):
        node1=F"server{i}"
        topo.add_node(node1)
        topo.add_link(node1, router1, IPv4Network(F"10.0.{i}.0/24"))
        set_link_properties(topo, node1, router1, bandwidth_source, delay, buffer, codel)

    gateways = []
    for i in range(1, receivers + 1):
        gateway=F"gw{i}"
        receiver=F"client{i}"
        topo.add_node(gateway, router=True)
        topo.add_node(receiver)

        topo.add_link(receiver, gateway, IPv4Network(F"10.1.{i}.0/24"))
        set_link_properties(topo, receiver, gateway, bandwidth_source, delay, buffer, codel)

        (bw, backup) = get_bw(i, receivers)
        topo.add_link(gateway, router2, IPv4Network(F"10.100.{i}.0/24"))
        set_link_properties(topo, gateway, router2, bw, delay, buffer, codel)
        topo.add_link(gateway, router3, IPv4Network(F"10.200.{i}.0/24"), backup=True)
        set_link_properties(topo, gateway, router3, backup, delay, buffer, codel)

        gateways.append(gateway)

    for i, router in enumerate(routers + gateways):
        conf = topo.get_conf(router)
        conf.glb.pim.set_ssm_range(IPv4Network("224.0.0.0/4"))
        conf.glb.isis.set_id(i + 1)
        conf.glb.ip.forward()

        peers = [peer["ip"] for peer in topo.get_peers_data(router)]
        conf.glb.bfd.set_peers(peers)

        for itf, data in topo.get_itfs(router):
            itf_conf = conf.get_interface(itf)
            itf_conf.pim.enable()
            if data["backup"]:
                itf_conf.isis.enable(weight=100)
            else:
                itf_conf.isis.enable()
            itf_conf.isis.enable_bfd()

    if args.mode == "setup":
        topo.run()
        print("Topology running")
        print()
        print("Hosts")
        print("Name\t\tIP\t\tBW\tBackup")
        for i in range(1, sources + 1):
            print(F"server{i}\t\t10.0.{i}.1")

        for i in range(1, receivers + 1):
            bw, backup = get_bw(i, receivers)
            print(F"client{i}\t\t10.1.{i}.1\t{str_bw(bw)}\t{str_bw(backup)}")
    else:
        topo.teardown()
