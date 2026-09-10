from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml


def parse_walltime(value) -> timedelta:
    return pd.Timedelta(value).to_pytimedelta()


@dataclass
class Server:
    cluster: str
    nodes: int = 1
    # Allow for a specific node (optional), e.g. "chirop-5.lille.grid5000.fr"
    node: Optional[str] = None


@dataclass
class Site:
    name: str
    cluster: str
    num_clients: int = 1


@dataclass
class Topology:
    name: str
    wall_time: timedelta
    frrouting_version: str
    relay_nodes: bool
    server: Server
    sites: list[Site]
    links: list[tuple[str, str]]

    # name helpers
    @staticmethod
    def router_role(site_name: str) -> str:
        return f"router_{site_name}"

    @staticmethod
    def client_role(site_name: str) -> str:
        return f"client_{site_name}"

    @staticmethod
    def relay_role(site_name: str) -> str:
        return f"relay_{site_name}"

    # all machines based on respective roles
    @property
    def router_roles(self) -> list[str]:
        return ["router_server", *(self.router_role(s.name) for s in self.sites)]

    @property
    def client_roles(self) -> list[str]:
        return [self.client_role(s.name) for s in self.sites]

    @property
    def relay_roles(self) -> list[str]:
        return [self.relay_role(s.name) for s in self.sites]

    # all clusters with clients, each with number of clients
    @property
    def client_clusters(self) -> list[dict]:
        return [
            {"cluster": s.cluster, "num_clients": s.num_clients} for s in self.sites
        ]

    @property
    def topology_links(self) -> list[tuple[str, str]]:
        return self.links

    # check links defined in topo file,
    # the endpoints of the links must be valid routers
    def validate(self) -> None:
        valid_routers = set(self.router_roles)
        for a, b in self.links:
            for endpoint in (a, b):
                if endpoint not in valid_routers:
                    raise ValueError(
                        f"link endpoint {endpoint!r} is not a known router role "
                        f"(known: {sorted(valid_routers)})"
                    )
        if len({s.name for s in self.sites}) != len(self.sites):
            raise ValueError("site names must be unique")


def load_topology(path: str | Path) -> Topology:
    path = Path(path)
    raw = yaml.safe_load(path.read_text()) or {}

    # allow both a file wrapped in `topology:` and a bare one
    topo_raw = raw.get("topology", raw)

    name = topo_raw.get("name")
    if not name:
        raise ValueError(f"{path}: missing 'topology.name'")

    # if walltime is missing, set it to 1hr
    walltime = parse_walltime(topo_raw.get("wall_time", "1hr"))

    use_relays: bool = topo_raw.get("relay_nodes", False)
    frr_ver = topo_raw.get("frrouting_version", "frr-10.4")

    server_raw = topo_raw.get("server") or {}
    server = Server(
        cluster=server_raw["cluster"],
        nodes=int(
            server_raw.get("nodes", 1)
        ),  # default to 1 server nodes, doesn't really work with more than 1
        node=server_raw.get("node"),
    )

    sites = [
        Site(
            name=site["name"],
            cluster=site["cluster"],
            num_clients=int(site.get("num_clients", 1)),  # default to 1 client
        )
        for site in (topo_raw.get("sites") or [])
    ]

    links = [tuple(l) for l in (topo_raw.get("links") or [])]

    topo = Topology(
        name=name,
        wall_time=walltime,
        server=server,
        sites=sites,
        links=links,
        relay_nodes=use_relays,
        frrouting_version=frr_ver
    )
    topo.validate()
    return topo
