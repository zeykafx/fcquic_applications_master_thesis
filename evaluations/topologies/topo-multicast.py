import argparse
from ipaddress import IPv4Address, IPv4Network

from topo import Topology

bandwidth_source = "30Mbit"
bandwidth_high = "12.5Mbit"
bandwidth_medium = "6.5Mbit"
bandwidth_low = "3.5Mbit"
delay = "1ms"
buffer = 250


def get_bw(client: int, heterogeneous: bool, proportions: dict[range, str]):
    if heterogeneous:
        for ran, bw in proportions.items():
            if client in ran:
                return bw
    else:
        return bandwidth_medium
    
    return ""


def set_link_properties(
    topo: Topology,
    node: str,
    itf: str,
    bw: str,
    delay: str,
    buffer: int,
    codel: bool = False,
):
    topo.set_bw(node, itf, bw)
    topo.set_delay(node, itf, delay)
    topo.set_limit(node, itf, buffer)
    topo.enable_codel(node, itf, codel)


def main():
    parser = argparse.ArgumentParser("topo")
    parser.add_argument("mode", choices=["setup", "teardown"])
    parser.add_argument("-s", "--sources", type=int, default=1)
    parser.add_argument("-r", "--receivers", type=int, default=2)
    parser.add_argument("--heterogeneous", action="store_true")
    parser.add_argument("--proportions", type=str, default="4,2,2")
    parser.add_argument("--cross-traffic", action="store_true")
    args = parser.parse_args()

    rates = [bandwidth_medium, bandwidth_low, bandwidth_high]
    clients_bws = {}
    count = 1
    for i, prop in enumerate(args.proportions.split(",")):
        val = int(prop)
        clients_bws[range(count, count + val)] = rates[i]
        count += val

    sources = args.sources
    receivers = args.receivers
    codel = args.cross_traffic

    topo = Topology()

    router1 = "router1"
    router2 = "router2"
    routers = [router1, router2]

    topo.add_node(router1, router=True)
    topo.add_node(router2, router=True)
    topo.add_link(router1, router2, IPv4Network("10.2.0.0/24"))
    set_link_properties(topo, router1, router2, bandwidth_source, delay, buffer, codel)

    for i in range(1, sources + 1):
        server = f"server{i}"
        topo.add_node(server)
        topo.add_link(server, router1, IPv4Network(f"10.0.{i}.0/24"))
        set_link_properties(
            topo, server, router1, bandwidth_source, delay, buffer, codel
        )

    for i in range(1, receivers + 1):
        client = f"client{i}"
        topo.add_node(client)
        topo.add_link(client, router2, IPv4Network(f"10.1.{i}.0/24"))
        bw = get_bw(i, args.heterogeneous, clients_bws)
        set_link_properties(topo, client, router2, bw, delay, buffer, codel)

    if args.cross_traffic:
        iperf_server = "iserver"
        topo.add_node(iperf_server)
        topo.add_link(iperf_server, router1, IPv4Network(f"10.0.{sources + 1}.0/24"))
        set_link_properties(
            topo, iperf_server, router1, bandwidth_source, delay, buffer, codel
        )

        iperf_client = "iclient"
        topo.add_node(iperf_client)
        topo.add_link(iperf_client, router2, IPv4Network(f"10.1.{receivers + 1}.0/24"))
        # higher bandwidth
        set_link_properties(
            topo, iperf_client, router2, bandwidth_source, delay, buffer, codel
        )

    topo.set_loopback(router1, IPv4Address("1.1.1.1"), 32)
    topo.set_loopback(router2, IPv4Address("2.2.2.2"), 32)

    for i, router in enumerate(routers):
        conf = topo.get_conf(router)

        # conf.glb.pim.set_ssm_range(IPv4Network("224.0.0.0/4"))
        conf.glb.pim.set_use_asm(True)
        conf.glb.pim.set_rp_priority(len(routers) - i)
        conf.glb.pim.set_asm_prefix(IPv4Network("224.0.0.0/4"))

        conf.glb.isis.set_id(i + 1)
        conf.glb.ip.forward()

        # enable isis and pim on loopback
        lo_conf = conf.get_interface("lo")
        lo_conf.isis.enable()
        lo_conf.isis.set_passive()
        lo_conf.pim.enable()

        for itf, _ in topo.get_itfs(router):
            itf_conf = conf.get_interface(itf)
            itf_conf.pim.enable()
            itf_conf.isis.enable()

    if args.mode == "setup":
        topo.run()
        print("Topology running")
        print()
        print("Hosts")
        print("Name\t\tIP\t\tBW")
        for i in range(1, sources + 1):
            print(f"server{i}\t\t10.0.{i}.1")

        for i in range(1, receivers + 1):
            bw = get_bw(i, args.heterogeneous, clients_bws)
            if bw == bandwidth_medium:
                bw = "Medium"
            elif bw == bandwidth_low:
                bw = "Low"
            else:
                bw = "High"
            print(f"client{i}\t\t10.1.{i}.1\t{bw}")

        print()
        if args.cross_traffic:
            print(f"iperf-server\t10.0.{sources + 1}.1")
            print(f"iperf-client\t10.1.{receivers + 1}.1")
    else:
        topo.teardown()


if __name__ == "__main__":
    main()
