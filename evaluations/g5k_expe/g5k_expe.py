from datetime import datetime, timedelta
import os
from pathlib import Path
from grid5000 import Grid5000
import enoslib as en

from topology import Topology, load_topology


class G5KExpe:
    def __init__(
        self,
        topology_conf: str | Path,
        g5k_conf_file_loc: str = ".python-grid5000.yaml",
        job_type: str = "deploy",
        os_env_name: str = "debian12-nfs",
    ):
        """
        Creates an instance of G5KExpe
        - `topology_conf`: path of the topology YAML file
        - `g5k_conf_file_loc`: path of the python-grid5000 file containing your G5K identifiers
        - `job_type`: defines the type of your job, likely should be "deploy"
        - `os_env_name`: name of the environment, see list here: https://www.grid5000.fr/w/Getting_Started#:~:text=On%20Grid%275000%20reference%20environments%5Bedit%5D
        """
        conf_file = os.path.join(os.environ.get("HOME"), g5k_conf_file_loc)  # type: ignore
        gk = Grid5000.from_yaml(conf_file)

        self.topology: Topology = load_topology(path=topology_conf)

        en.set_config(ansible_forks=100)
        self.job_type = job_type
        self.env_name = os_env_name

        # map each cluster to its site
        self.cluster_to_site = {}
        for site in gk.sites.list():
            for cluster in site.clusters.list():
                self.cluster_to_site[cluster.uid] = site.uid

    def usage_policy_check(self):
        datetime_now = datetime.now()
        job_end_dt = datetime_now + self.topology.wall_time
        if datetime_now.hour <= 17 and job_end_dt.hour >= 19:
            raise RuntimeError(
                "This job reservation will violate the usage policy and will cross the day night boundary"
            )

    def setup_enoslib_conf(self) -> en.G5k:
        """
        Sets up the enoslib reservation for the test as defined in the topology file
        Returns the G5k `provider` object containing the machines to reserve,...
        """
        # Display some general information about the library
        en.check()
        # Enable rich logging
        _ = en.init_logging()

        server_cluster = self.cluster_to_site[self.topology.server.cluster]

        conf = (
            en.G5kConf.from_settings(
                job_name=self.topology.name,
                walltime=str(self.topology.wall_time),
                env_name=self.env_name,
                job_type=[self.job_type],
            )
            # server router
            .add_machine(
                roles=["router", "router_server"],
                cluster=self.topology.server.cluster,
                nodes=1,
            )
            .add_machine(
                roles=["server"],
                # servers=["chirop-5.lille.grid5000.fr"],
                site=server_cluster,
                nodes=self.topology.server.nodes,
            )
            .add_network(
                id="subnet_server",
                type="slash_22",
                roles=["subnet", "subnet_server"],
                site=server_cluster,
            )
        )

        # we need to add one client router + clients + relay + subnet for each client cluster

        for i, client_cluster in enumerate(self.topology.client_clusters):

            conf = (
                conf
                # add only one client router
                .add_machine(
                    roles=["router", "router_client", f"router_client_{i}"],
                    cluster=client_cluster["cluster"],
                    nodes=1,
                )
                # add all of the client machines
                .add_machine(
                    roles=["client", f"client_{i}"],
                    cluster=client_cluster["cluster"],
                    nodes=client_cluster["num_clients"],
                ).add_network(
                    id=f"subnet_client_{i}",
                    type="slash_22",
                    roles=["subnet", "subnet_client", f"subnet_client_{i}"],
                    site=self.cluster_to_site[client_cluster["cluster"]],
                )
            )
            if self.topology.relay_nodes:
                # if relays are used, then add one relay machine per client cluster
                conf = conf.add_machine(
                    roles=["relay", f"relay_{i}"],
                    cluster=client_cluster["cluster"],
                    nodes=1,
                )

        # This will validate the configuration, but not reserve resources yet
        provider = en.G5k(conf)
        return provider

    def reserve_res(self, provider: en.G5k) -> en.Roles:
        """
        Reserves the resources as defined in `provider`
        Returns the roles obtained (or not) following the reservation
        """
        print("Reserving resources now, might take a while...")

        # Get actual resources
        roles, networks = provider.init()

        print("Obtained resources:")
        print(f"Roles: {roles}")
        print(f"Networks: {networks}")

        # Fill in network information from nodes
        roles: en.Roles = en.sync_info(roles, networks)

        with en.actions(roles=roles) as a:
            a.apt(task_name="Install traceroute", name="traceroute", state="present")
            a.apt(task_name="Install btop", name="btop", state="present")
            a.apt(task_name="Install htop", name="htop", state="present")
            a.apt(task_name="Install tcpdump", name="tcpdump", state="present")
            a.apt(
                task_name="Install python",
                name=["python3-pip", "python-is-python3"],
                state="present",
            )

        with en.actions(roles=roles["router"], gather_facts=True) as a:
            a.file(
                task_name="Ensure apt keyring directory exists",
                path="/usr/share/keyrings",
                state="directory",
                mode="0755",
            )
            a.get_url(
                task_name="Download FRR GPG key",
                url="https://deb.frrouting.org/frr/keys.gpg",
                dest="/usr/share/keyrings/frrouting.gpg",
                mode="0644",
            )
            a.apt_repository(
                task_name="Add FRR apt repository",
                repo="deb [signed-by=/usr/share/keyrings/frrouting.gpg] https://deb.frrouting.org/frr {{ ansible_distribution_release }} " + self.topology.frrouting_version,
                filename="frr",
                state="present",
            )
            a.apt(
                task_name="Install FRR packages",
                name=["frr", "frr-pythontools"],
                state="present",
                update_cache=True,
            )
            results = a.results
            print(f"Results ")

        return roles
