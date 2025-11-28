import argparse
import os
from ipaddress import IPv4Address, IPv4Network

import yaml
from topo import Topology

bandwidth_source = "30Mbit"
bandwidth_high = "12.5Mbit"
bandwidth_medium = "6.5Mbit"
bandwidth_low = "3.5Mbit"
delay = "1ms"
buffer = 250
codel = False


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


def file_path(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(
            f"readable_dir:{path} is not a valid file path"
        )


def main():
    parser = argparse.ArgumentParser("topo")
    parser.add_argument("config_path", type=file_path)
    parser.add_argument("mode", choices=["setup", "teardown"])
    parser.add_argument("-v", "--verbose", default=False)

    args = parser.parse_args()
    verbose = args.verbose

    # rates = [bandwidth_medium, bandwidth_low, bandwidth_high]
    # clients_bws = {}
    # count = 1
    # for i, prop in enumerate(args.proportions.split(",")):
    #     val = int(prop)
    #     clients_bws[range(count, count + val)] = rates[i]
    #     count += val

    conf_file = args.config_path
    routers = []
    servers = []
    clients = []
    links = []
    with open(conf_file) as conf_fd:
        conf_yml = yaml.safe_load(conf_fd)
        if "topology" not in conf_yml:
            raise Exception(
                f"Topology key not found in configuration file {conf_file}!"
            )

        topology = conf_yml["topology"]
        # keys below are required keys
        keys = ["routers", "clients", "servers", "links"]
        # if any of these keys are not in the config file, throw an error
        if not all(key in topology for key in keys):
            missing = [key for key in keys if key not in topology]
            raise Exception(
                f"Key(s) '{', '.join(missing)}' not found in configuration file {conf_file}!"
            )

        routers = topology["routers"]
        servers = topology["servers"]
        clients = topology["clients"]
        links = topology["links"]

    topo = Topology()

    # topo.add_node(router1, router=True)
    # topo.add_node(router2, router=True)
    # topo.add_link(router1, router2, IPv4Network("10.2.0.0/24"))
    # set_link_properties(topo, router1, router2, bandwidth_source, delay, buffer, codel)

    for id, router in enumerate(routers):
        if verbose:
            print(f"Adding router {router} (id: {id}")

        topo.add_node(router, router=True)
        topo.set_loopback(router, IPv4Address(f"10.255.1.{id}"), 32)

    for server in servers:
        if verbose:
            print(f"Adding server {server}")

        topo.add_node(server)

    for client in clients:
        if verbose:
            print(f"Adding client {client}")

        topo.add_node(client)

    router_links = 0
    other_links = 0
    server_ips = []
    client_ips = []
    for link in links:
        endpoints = link["endpoints"]
        node1 = endpoints[0]
        node2 = endpoints[1]

        both_routers = True if "routers" in link else False

        network = None
        if both_routers:
            network = IPv4Network(f"10.100.{router_links}.0/24")
            router_links += 1
        else:
            network = IPv4Network(f"10.10.{other_links}.0/24")
            other_links += 1

        topo.add_link(node1, node2, network)

        # If any of the two nodes is a server or a client, record the a tuple (node, ip)
        for node, other in [(node1, node2), (node2, node1)]:
            if node in servers:
                server_ips.append((node, topo.get_ip(node, other)))
            elif node in clients:
                client_ips.append((node, topo.get_ip(node, other)))

        # if node1 in servers: 
        #     server_ips.append((node1, topo.get_ip(node1, node2)))
        # elif node2 in servers:
        #     server_ips.append((node2, topo.get_ip(node2, node1)))

        # if node1 in clients:
        #     client_ips.append((node1, topo.get_ip(node1, node2)))
        # elif node2 in clients:
        #     client_ips.append((node2, topo.get_ip(node2, node1)))

        bw = link["bw"] if "bw" in link else bandwidth_high
        set_link_properties(topo, node1, node2, bw, delay, buffer)
        if verbose:
            print(
                f"Adding link: {node1} <-> {node2}, Network: {network}, Bandwidth: {bw}"
            )

    for id, router in enumerate(routers):
        if verbose:
            print(f"Setting up router {router}")

        conf = topo.get_conf(router)

        conf.glb.pim.set_use_asm(True)
        conf.glb.pim.set_rp_priority(id)
        conf.glb.pim.set_asm_prefix(IPv4Network("224.0.0.0/4"))

        conf.glb.isis.set_id(id + 1)
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

        for server, server_ip in server_ips:
            print(f"{server}\t\t{server_ip}")

        for client, client_ip in client_ips:
            # bw = get_bw(i, args.heterogeneous, clients_bws)
            # if bw == bandwidth_medium:
            #     bw = "Medium"
            # elif bw == bandwidth_low:
            #     bw = "Low"
            # else:
            #     bw = "High"
            print(f"{client}\t\t{client_ip}")

        print()
    else:
        topo.teardown()


if __name__ == "__main__":
    main()
