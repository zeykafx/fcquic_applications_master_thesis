import os
import shutil
import subprocess
from ipaddress import IPv4Address, IPv4Network

import graphviz
import networkx as nx
from frrouting import FRRouting


class Topology:
    def __init__(self):
        self.count = 0
        self.ids = {}
        self.graph = nx.DiGraph()

    def add_node(self, node: str, router=False):
        if node not in self.graph:
            self.graph.add_node(
                node, conf=FRRouting() if router else None, router=router
            )
            self.ids[node] = self.count
            self.count += 1
        return self.ids[node]

    def add_link(
        self, node1: str, node2: str, network: IPv4Network, backup: bool = False
    ):
        self.add_node(node1)
        self.add_node(node2)
        itf1 = f"{node1}-{node2}"
        itf2 = f"{node2}-{node1}"
        self.graph.add_edge(node1, node2, itf=itf1, peer_itf=itf2)
        self.graph.add_edge(node2, node1, itf=itf2, peer_itf=itf1)

        conf1 = self.get_conf(node1)
        if conf1 is not None:
            conf1.add_interface(itf1)
        conf2 = self.get_conf(node2)
        if conf2 is not None:
            conf2.add_interface(itf2)

        self._set_link_property(node1, node2, "backup", backup)

        ip1, ip2 = list(network.hosts())[:2]
        self.set_ip(node1, node2, ip1, network.prefixlen)
        self.set_ip(node2, node1, ip2, network.prefixlen)

    def get_itf_info(self, node1, node2):
        return self.graph.get_edge_data(node1, node2)

    def set_ip(self, node1, node2, ip: IPv4Address, prefix: int):
        info = self.get_itf_info(node1, node2)
        info["ip"] = ip
        info["prefix"] = prefix
        conf = self.get_conf(node1)
        if conf is not None:
            conf.get_interface(info["itf"]).ip.set_addr(
                IPv4Network(f"{ip}/{prefix}", strict=False)
            )

    def get_ip(self, node1, node2):
        info = self.get_itf_info(node1, node2)
        return info["ip"]

    def _set_link_property(self, node1, node2, property: str, value):
        info = self.get_itf_info(node1, node2)
        info[property] = value
        info = self.get_itf_info(node2, node1)
        info[property] = value

    def set_bw(self, node1, node2, bw):
        self._set_link_property(node1, node2, "bw", bw)

    def set_delay(self, node1, node2, delay):
        self._set_link_property(node1, node2, "delay", delay)

    def set_limit(self, node1, node2, limit):
        self._set_link_property(node1, node2, "limit", limit)

    def enable_codel(self, node1, node2, enabled: bool):
        self._set_link_property(node1, node2, "codel", enabled)

    def set_loss_percentage(self, node1, node2, percentage):
        self._set_link_property(node1, node2, "loss_percentage", percentage)

    def set_burst_percentage(self, node1, node2, percentage):
        self._set_link_property(node1, node2, "burst_percentage", percentage)

    def set_multicast_enabled(self, node1, node2, multicast):
        self._set_link_property(node1, node2, "multicast", multicast)

    def get_itfs(self, node: str):
        itfs = []
        for _, _, info in self.graph.edges(node, data=True):
            itfs.append((info["itf"], info))
        return itfs

    def get_peers_data(self, node: str):
        peers = list(self.graph.edges(node, data=True))
        peer_info = []
        for _, peer, _ in peers:
            peer_info.append(self.graph.get_edge_data(peer, node))

        return peer_info

    def get_conf(self, node: str) -> FRRouting:
        return self.graph.nodes(data=True)[node]["conf"]

    def _get_node_ip(self, node: str):
        edges = list(self.graph.edges(node, data=True))
        if edges:
            _, _, info = edges[0]
            if "ip" in info:
                return str(info["ip"])
        return None

    def _has_multicast_disabled(self, node: str):
        for _, _, info in self.graph.edges(node, data=True):

            if info.get("multicast") is False:
                return True
        return False

    def draw_diagram(self, filename="diagram"):
        # graph is used because it's bidirectional links
        dot = graphviz.Graph(filename, format="svg", engine="neato")
        dot.attr(overlap="vpsc", splines="true", sep="+30", esep="+5", normalize="0")

        for node in self.graph.nodes:
            # check if node has multicast disabled on any link
            multicast_disabled = self._has_multicast_disabled(node)

            if self._is_router(node):
                # when disabling multicast for a router, the pim router section will not has "use_asm" set to true
                multicast_disabled = not self.get_conf(node).glb.pim.use_asm
                fillcolor = "lightcoral" if multicast_disabled else "lightblue"
                dot.node(
                    node, node, shape="circle", style="filled", fillcolor=fillcolor
                )
            elif node.startswith("source") or node.startswith("server"):
                # server
                ip = self._get_node_ip(node)
                label = f"{node}\n{ip}" if ip else node
                fillcolor = "lightcoral" if multicast_disabled else "lightgreen"
                dot.node(node, label, shape="box", style="filled", fillcolor=fillcolor)
            else:
                # Client
                ip = self._get_node_ip(node)
                label = f"{node}\n{ip}" if ip else node
                fillcolor = "lightyellow"
                dot.node(
                    node, label, shape="ellipse", style="filled", fillcolor=fillcolor
                )

        drawn_edges = set()
        for node1, node2, info in self.graph.edges(data=True):
            edge_key = tuple(sorted([node1, node2]))
            if edge_key not in drawn_edges:
                drawn_edges.add(edge_key)
                # check if multicast is disabled on this link
                multicast_disabled = info.get("multicast") is False
                color = "red" if multicast_disabled else "black"
                penwidth = "2.0" if multicast_disabled else "1.0"
                
                # display loss rate and the delay on the label if it's higher than 0% and 0ms
                loss_rate = info.get("loss_percentage")
                delay = info.get("delay")
                loss_str = loss_rate if loss_rate != "0%" else ""
                delay_str = delay if delay != "0ms" else ""
                label_str = f"{loss_str}\n{delay_str}"
                dot.edge(
                    node1,
                    node2,
                    color=color,
                    penwidth=penwidth,
                    headlabel=label_str,
                    labeldistance="3.0",
                    labelfontsize="15",
                )
        dot.render(cleanup=True)

    def _create_node(self, node: str):
        subprocess.run(["ip", "netns", "add", f"{node}"])
        subprocess.run(
            ["ip", "netns", "exec", f"{node}", "ip", "link", "set", "dev", "lo", "up"]
        )

    def _create_link(self, node1, node2, data):
        itf1 = data["itf"]
        itf2 = data["peer_itf"]
        subprocess.run(
            ["ip", "link", "add", f"{itf1}", "type", "veth", "peer", "name", f"{itf2}"]
        )

        # assign to correct namespace
        subprocess.run(["ip", "link", "set", f"{itf1}", "netns", f"{node1}"])
        subprocess.run(["ip", "link", "set", f"{itf2}", "netns", f"{node2}"])

        # set interfaces up
        subprocess.run(
            [
                "ip",
                "netns",
                "exec",
                f"{node1}",
                "ip",
                "link",
                "set",
                "dev",
                f"{itf1}",
                "up",
            ]
        )
        subprocess.run(
            [
                "ip",
                "netns",
                "exec",
                f"{node2}",
                "ip",
                "link",
                "set",
                "dev",
                f"{itf2}",
                "up",
            ]
        )

    def _add_ips(self, node):
        for _, _, info in self.graph.edges(node, data=True):
            if "ip" in info:
                subprocess.run(
                    [
                        "ip",
                        "netns",
                        "exec",
                        f"{node}",
                        "ip",
                        "addr",
                        "add",
                        f"{info['ip']}/{info['prefix']}",
                        "dev",
                        f"{info['itf']}",
                    ]
                )

    def _set_netem(self, node, data):
        delay = data.get("delay", "0ms")
        bw = data.get("bw", "100Mbit")
        limit = str(data.get("limit", "10000"))
        codel = data.get("codel", False)
        loss_percentage = data.get("loss_percentage", "0%")
        burst_percentage = data.get("burst_percentage", "25%")
        cmd = [
            "ip",
            "netns",
            "exec",
            f"{node}",
            "tc",
            "qdisc",
            "add",
            "dev",
            f"{data['itf']}",
            "root",
            "handle",
            "1:",
            "netem",
            "delay",
            delay,
            "rate",
            bw,
            "limit",
            limit,
        ]
        if loss_percentage != "0%":
            cmd.extend(["loss", loss_percentage, burst_percentage])
        subprocess.run(cmd)
        if codel:
            subprocess.run(
                [
                    "ip",
                    "netns",
                    "exec",
                    f"{node}",
                    "tc",
                    "qdisc",
                    "add",
                    "dev",
                    f"{data['itf']}",
                    "parent",
                    "1:1",
                    "handle",
                    "2:",
                    "fq_codel",
                ]
            )

    def _add_route(self, node):
        (_, peer, _) = list(self.graph.edges(node, data=True))[0]
        peer_info = self.graph.get_edge_data(peer, node)

        subprocess.run(
            [
                "ip",
                "netns",
                "exec",
                f"{node}",
                "ip",
                "route",
                "add",
                "default",
                "via",
                f"{peer_info['ip']}",
            ]
        )

    def _is_router(self, node):
        return self.graph.nodes(data=True)[node]["router"]

    def set_loopback(self, node: str, ip: IPv4Address, prefix: int = 32):
        if not self._is_router(node):
            return

        # store loopback info in node attr
        node_data = self.graph.nodes[node]
        node_data["loopback_ip"] = ip
        node_data["loopback_prefix"] = prefix

        # add loopback iface to frr config
        conf = self.get_conf(node)
        if conf is not None:
            conf.add_interface("lo")
            conf.get_interface("lo").ip.set_addr(
                IPv4Network(f"{ip}/{prefix}", strict=False)
            )

    def _configure_loopback(self, node: str):
        node_data = self.graph.nodes[node]
        if "loopback_ip" in node_data:
            ip = node_data["loopback_ip"]
            prefix = node_data["loopback_prefix"]
            subprocess.run(
                [
                    "ip",
                    "netns",
                    "exec",
                    f"{node}",
                    "ip",
                    "addr",
                    "add",
                    f"{ip}/{prefix}",
                    "dev",
                    "lo",
                ]
            )

    def _dump_conf(self, node: str):
        conf = self.get_conf(node)
        with open(f"{node}.conf", "w") as file:
            file.write(str(conf))

    def _start_frrouting(self, node):
        path = "/usr/lib/frr"  # installed manually
        os.makedirs(f"/etc/frr/{node}", exist_ok=True)

        shutil.copyfile("./daemons", f"/etc/frr/{node}/daemons")
        shutil.copyfile(f"{node}.conf", f"/etc/frr/{node}/frr.conf")
        subprocess.run(
            [f"{path}/frrinit.sh", "start", node],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        pass

    def _stop_frrouting(self, node):
        path = "/usr/lib/frr"  # installed manually
        subprocess.run(
            [f"{path}/frrinit.sh", "stop", node],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        shutil.rmtree(f"/etc/frr/{node}")
        os.remove(f"{node}.conf")

    def run(self):
        for node in self.graph.nodes:
            self._create_node(node)

        for node1, node2, info in self.graph.edges(data=True):
            if node1 > node2:
                continue
            self._create_link(node1, node2, info)

        for node1, _, info in self.graph.edges(data=True):
            self._set_netem(node1, info)

        for node, info in self.graph.nodes(data=True):
            self._add_ips(node)
            if self._is_router(node):
                self._configure_loopback(node)
                self._dump_conf(node)
                self._start_frrouting(node)
            else:
                self._add_route(node)

    def _teardown_node(self, node: str):
        subprocess.run(["ip", "netns", "del", f"{node}"])

    def teardown(self):
        for node in self.graph.nodes:
            if self._is_router(node):
                self._stop_frrouting(node)
            self._teardown_node(node)
