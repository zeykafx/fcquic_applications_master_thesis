import argparse
import os
from ipaddress import IPv4Address, IPv4Network

import yaml
from topo import Topology

bandwidth_source = "30Mbit"
bandwidth_high = "12.5Mbit"
bandwidth_medium = "6.5Mbit"
bandwidth_low = "3.5Mbit"

default_delay = "1ms"
default_buffer = 250
default_codel = False
default_loss = 0
default_loss_burst_percentage = 25


def set_link_properties(
    topo: Topology,
    node: str,
    itf: str,
    bw: str,
    delay: str,
    buffer: int,
    loss: int,
    loss_burst_percentage: int = default_loss_burst_percentage,
    codel: bool = False,
):
    topo.set_bw(node, itf, bw)
    topo.set_delay(node, itf, delay)
    topo.set_limit(node, itf, buffer)
    topo.set_loss_percentage(node, itf, loss)
    topo.set_burst_percentage(node, itf, loss_burst_percentage)
    topo.enable_codel(node, itf, codel)


def file_path(path):
    if os.path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid file path")


def parse_config_file(
    filepath: str,
):
    with open(filepath) as conf_fd:
        conf_yml = yaml.safe_load(conf_fd)
        if "topology" not in conf_yml:
            raise Exception(f"Topology key not found in configuration file {filepath}!")

        topology = conf_yml["topology"]
        # keys below are required keys
        keys = ["routers", "clients", "servers", "links"]
        # if any of these keys are not in the config file, throw an error
        if not all(key in topology for key in keys):
            missing = [key for key in keys if key not in topology]
            raise Exception(
                f"Key(s) '{', '.join(missing)}' not found in configuration file {filepath}!"
            )

        # return a tuple with the list of routers, servers, clients, and links
        return (topology[key] for key in keys)


def main():
    parser = argparse.ArgumentParser("topo")
    parser.add_argument("config_path", type=file_path)
    parser.add_argument("mode", choices=["setup", "teardown"])
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    verbose = args.verbose

    conf_file = args.config_path

    routers, servers, clients, links = parse_config_file(conf_file)

    topo = Topology()

    for id, router in enumerate(routers):
        if verbose:
            print(f"Adding router {router} (id: {id})")

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

    # for each link in the config, add a link between the two nodese, set the bandwidth, loss,...
    router_links, other_links = 0, 0
    server_ips, client_ips = [], []
    clients_tc = {}
    servers_tc = {}

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

        bw = link["bandwidth"] if "bandwidth" in link else bandwidth_high
        loss_percentage = link["loss"] if "loss" in link else default_loss
        set_link_properties(
            topo, node1, node2, bw, default_delay, default_buffer, loss_percentage
        )

        client_node = node1 if node1 in clients else node2
        clients_tc[client_node] = (bw, loss_percentage)
        
        server_node = node1 if node1 in servers else node2
        servers_tc[server_node] = (bw, loss_percentage)

        if verbose:
            print(
                f"Adding link: {node1} <-> {node2}, Network: {network}, Bandwidth: {bw}, Loss: {loss_percentage}"
            )

    # setup the routers' interfaces
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
        print("Name\t\tIP\t\tBW\tLOSS")

        for server, server_ip in server_ips:
            bw, loss = servers_tc[server]
            print(f"{server}\t\t{server_ip}\t{bw}\t{loss}")

        for client, client_ip in client_ips:
            bw, loss = clients_tc[client]
            print(f"{client}\t\t{client_ip}\t{bw}\t{loss}")

        print()
    else:
        topo.teardown()


if __name__ == "__main__":
    main()
