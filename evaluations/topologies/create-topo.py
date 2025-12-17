# Original Author: Anthony Doeraene
# Modifications made by Corentin Detry

import argparse
import os
from ipaddress import IPv4Address, IPv4Network

import yaml
from topo import Topology

verbose = False

bandwidth_source = "30Mbit"
bandwidth_high = "12.5Mbit"
bandwidth_medium = "6.5Mbit"
bandwidth_low = "3.5Mbit"

default_bandwidth = bandwidth_source
default_multicast_enabled_router = True
default_multicast_enabled_link = True
default_delay = "1ms"
default_buffer = 1000  # buffer size in packets
default_loss = "0%"
default_loss_burst_percentage = "10%"
default_rp_id = 1
default_asm_prefix = "224.0.0.0/4"
router_overrides = {}


def set_link_properties(
    topo: Topology,
    node: str,
    itf: str,
    bw: str,
    delay: str,
    buffer: int,
    loss: str,
    multicast: bool,
    loss_burst_percentage: str = default_loss_burst_percentage,
    codel: bool = False,
):
    topo.set_bw(node, itf, bw)
    topo.set_delay(node, itf, delay)
    topo.set_limit(node, itf, buffer)
    topo.set_loss_percentage(node, itf, loss)
    topo.set_multicast_enabled(node, itf, multicast)
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
        keys = ["defaults", "routers", "servers", "clients", "links"]
        # if any of these keys are not in the config file, throw an error
        if not all(key in topology for key in keys):
            missing = [key for key in keys if key not in topology]
            raise Exception(
                f"Key(s) '{', '.join(missing)}' not found in configuration file {filepath}!"
            )

        # return a tuple with the list of routers, servers, clients, and links
        return (
            topology["defaults"],
            topology["routers"],
            topology["servers"],
            topology["clients"],
            topology["links"],
        )


def parse_defaults(defaults: dict):
    global \
        default_multicast_enabled, \
        default_bandwidth, \
        default_buffer, \
        default_delay, \
        default_loss, \
        default_loss_burst_percentage, \
        default_multicast_enabled_link

    if "routers" in defaults and "multicast" in defaults["routers"]:
        default_multicast_enabled = defaults["routers"]["multicast"]

    if "links" in defaults:
        if "bandwidth" in defaults["links"]:
            default_bandwidth = defaults["links"]["bandwidth"]
        if "loss" in defaults["links"]:
            default_loss = defaults["links"]["loss"]
        if "burst" in defaults["links"]:
            default_loss_burst_percentage = defaults["links"]["burst"]
        if "delay" in defaults["links"]:
            default_delay = defaults["links"]["delay"]
        if "buffer" in defaults["links"]:
            default_buffer = defaults["links"]["buffer"]

        if "multicast" in defaults["links"]:
            default_multicast_enabled_link = defaults["links"]["multicast"]


def parse_routers(routers, topo: Topology, ips, tc_info):
    # collect the router ids in a list and return it
    routers_list = []

    # TODO: define router links in this case
    if type(routers) is list:
        # ['router1', 'router2', 'router3']
        for id, router in enumerate(routers):
            routers_list.append(router)
            if verbose:
                print(f"Adding router: {router} (id: {id})")

            topo.add_node(router, router=True)
            lo_ip = IPv4Address(f"10.255.1.{id}")
            ips[router] = lo_ip
            topo.set_loopback(router, lo_ip, 32)

    else:
        # {'num': 3, 'overrides': {'router1': {'multicast': False}}, 'links': [{'endpoints': ['router1', 'router2']}, {'endpoints': ['router1', 'router3']}, {'endpoints': ['router2', 'router3']}]}

        # We can specify how many routers we want
        # e.g., "num: 4" will result in r1, r2, r3, and r4 to be created
        if "num" in routers:
            for id in range(1, routers["num"] + 1):
                router = f"r{id}"  # Note: don't use router{id} because that can be too long for the interface names
                routers_list.append(router)

                if verbose:
                    print(f"Adding router: {router} (id: {id})")

                topo.add_node(router, router=True)
                lo_ip = IPv4Address(f"10.255.1.{id}")
                ips[router] = lo_ip
                topo.set_loopback(router, lo_ip, 32)

        elif "list" in routers:
            # if "num" is not specified, then we can have a list of router names under the "list" key
            # ["router1", "router2"]
            for id, router in enumerate(routers["list"]):
                routers_list.append(router)
                if verbose:
                    print(f"Adding router: {router} (id: {id})")

                topo.add_node(router, router=True)
                lo_ip = IPv4Address(f"10.255.1.{id}")
                ips[router] = lo_ip
                topo.set_loopback(router, lo_ip, 32)

        if "overrides" in routers:
            for router, val in routers["overrides"].items():
                if "multicast" in val:
                    router_overrides[router] = {}
                    router_overrides[router]["multicast"] = val["multicast"]

        if "links" in routers:
            router_links = 0
            for link in routers["links"]:
                router_links, _, _ = configure_link(
                    link, router_links, {}, {}, [], [], [], topo, router_link=True
                )

    return routers_list, ips, tc_info


def parse_clients(clients, topo: Topology):
    clients_list = []
    if type(clients) is list:
        for client in clients:
            clients_list.append(client)
            if verbose:
                print(f"Adding client: {client}")

            topo.add_node(client)
    else:
        if "num" in clients:
            for id in range(1, clients["num"] + 1):
                client = f"client{id}"
                clients_list.append(client)
                if verbose:
                    print(f"Adding client {client} (id: {id})")

                topo.add_node(client)
    return clients_list


def configure_link(
    link,
    link_ctr: int,
    tc_info: dict,
    ips: dict,
    servers: list,
    routers: list,
    clients: list,
    topo: Topology,
    router_link: bool = False,
):
    endpoints = link["endpoints"]
    node1 = endpoints[0]
    node2 = endpoints[1]

    if not router_link and (node1 in routers and node2 in routers):
        router_link = True

    network = None
    if router_link:
        network = IPv4Network(f"10.100.{link_ctr}.0/24")
        link_ctr += 1
    else:
        network = IPv4Network(f"10.10.{link_ctr}.0/24")
        link_ctr += 1

    topo.add_link(node1, node2, network)

    if not router_link:
        # If any of the two nodes is a server or a client, record the a tuple (node, ip)
        for node, other in [(node1, node2), (node2, node1)]:
            if node in servers or node in clients:
                ips[node] = topo.get_ip(node, other)

    bw = link["bandwidth"] if "bandwidth" in link else default_bandwidth
    loss_percentage = link["loss"] if "loss" in link else default_loss
    burst_percentage = (
        link["burst"] if "burst" in link else default_loss_burst_percentage
    )
    delay = link["delay"] if "delay" in link else default_delay
    buffer = link["buffer"] if "buffer" in link else default_buffer
    multicast = (
        link["multicast"] if "multicast" in link else default_multicast_enabled_link
    )
    set_link_properties(
        topo,
        node1,
        node2,
        bw,
        delay,
        buffer,
        loss_percentage,
        multicast,
        burst_percentage,
    )

    if not router_link:
        client_node = node1 if node1 in clients else node2
        tc_info[client_node] = (bw, loss_percentage, delay, buffer, multicast)

        server_node = node1 if node1 in servers else node2
        tc_info[server_node] = (bw, loss_percentage, delay, buffer, multicast)

    if verbose:
        print(
            f"Adding link: {node1} <-> {node2}, Network: {network}, bw: {bw}, loss: {loss_percentage}, delay: {delay}, buf: {buffer}, pim: {multicast}"
        )
    return link_ctr, tc_info, ips


def main():
    global verbose
    parser = argparse.ArgumentParser("topo")
    parser.add_argument("config_path", type=file_path)
    parser.add_argument("mode", choices=["setup", "teardown"])
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "-d",
        "--draw",
        action="store_true",
        help="Outputs an svg diagram representing the topology",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Create the topology but don't run it, useful to check syntax or diagram",
    )

    args = parser.parse_args()
    verbose = args.verbose

    conf_file = args.config_path

    defaults, routers, servers, clients, links = parse_config_file(conf_file)

    draw_diagram = args.draw
    config_dir = os.path.dirname(conf_file)
    diagram_filename = os.path.join(config_dir, "diagram")

    parse_defaults(defaults)

    topo = Topology()

    ips = {}
    tc_info = {}
    routers_list, ips, tc_info = parse_routers(routers, topo, ips, tc_info)

    for server in servers:
        if verbose:
            print(f"Adding server: {server}")

        topo.add_node(server)

    clients_list = parse_clients(clients, topo)

    # for each link in the config, add a link between the two nodese, set the bandwidth, loss,...
    other_links = 0

    for link in links:
        other_links, tc_info, ips = configure_link(
            link, other_links, tc_info, ips, servers, routers_list, clients_list, topo
        )

    # setup the routers' interfaces
    for r_id, router in enumerate(routers_list):
        id = (
            r_id + 1
        )  # since the router ids go from 1 to n, here enumerate starts at 0 so we must increase by 1 to get what we expect
        if verbose:
            print(f"Setting up router: {router} (id {id})")

        conf = topo.get_conf(router)

        conf.glb.isis.set_id(id + 1)
        conf.glb.ip.forward()

        # check if the router must have multicast enabled or disabled
        multicast_enabled = (
            router_overrides[router]["multicast"]
            if router in router_overrides
            else default_multicast_enabled
        )

        if multicast_enabled:
            # note: highest bsr priority wins
            # but lowest rp priority wins
            bsr_priority = id
            rp_priority = id + 100

            if default_rp_id == id:
                bsr_priority = id + 100  # highest wins
                rp_priority = 0  # lowest wins

            conf.glb.pim.set_use_asm(True)
            conf.glb.pim.set_bsr_priority(bsr_priority)
            conf.glb.pim.set_rp_priority(rp_priority)

            conf.glb.pim.set_asm_prefix(IPv4Network(default_asm_prefix))

        # enable isis and pim on loopback
        lo_conf = conf.get_interface("lo")
        lo_conf.isis.enable()
        lo_conf.isis.set_passive()

        # enable pim on the loopback interface if this router has multicast enabled
        if multicast_enabled:
            lo_conf.pim.enable()

        for itf, info in topo.get_itfs(router):
            itf_conf = conf.get_interface(itf)
            itf_conf.isis.enable()

            # multicast is enabled on this interface if info["multicast"] is True, if it's undefined, then we use the default value (True)
            itf_mcast_enabled = (
                info["multicast"]
                if "multicast" in info
                else default_multicast_enabled_link
            )

            if itf_mcast_enabled:
                itf_conf.pim.enable()

    if args.mode == "setup":
        if draw_diagram:
            topo.draw_diagram(diagram_filename)
            print(f"Topology diagram generated: {diagram_filename}.gv.svg")

        if not args.preview:
            topo.run()
            print("Topology running")

        print()

        print(f"RP/BSR Router ID: {default_rp_id}")
        print("Name\t\tIP\t\tBW\tLOSS\tDELAY\tBUFFER\tMulticast")

        for node, ip in ips.items():
            bw, loss, delay, buffer, multicast = "n/a\t", "n/a", "n/a", "n/a", "n/a"
            if node in tc_info:
                bw, loss, delay, buffer, multicast = tc_info[node]

            if node in routers_list:
                multicast_enabled = (
                    router_overrides[node]["multicast"]
                    if node in router_overrides
                    else default_multicast_enabled
                )
                print(f"{node}\t\t{ip}\tn/a\tn/a\tn/a\tn/a\t{multicast_enabled}")
            else:
                print(f"{node}\t\t{ip}\t{bw}\t{loss}\t{delay}\t{buffer}\t{multicast}")

    else:
        topo.teardown()


if __name__ == "__main__":
    main()
