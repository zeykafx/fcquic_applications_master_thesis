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

    def setup_en_conf(self):
        # Display some general information about the library
        en.check()
        # Enable rich logging
        _ = en.init_logging()

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
            # # server
            # .add_machine(
            #     roles=["server"],
            #     servers=["chirop-5.lille.grid5000.fr"],
            #     # cluster=SERVER_CLUSTER,
            #     # nodes=NUM_SERVER_NODES,
            # ).add_network(
            #     id="subnet_server",
            #     type="slash_22",
            #     roles=["subnet", "subnet_server"],
            #     site=cluster_to_site[SERVER_CLUSTER],
            # )
        )
        for i, serv in enumerate(self.topology.server.nodes):
            conf = conf.add_machine(
                roles=["server"],
                servers=["chirop-5.lille.grid5000.fr"],
                # cluster=SERVER_CLUSTER,
                # nodes=NUM_SERVER_NODES,
            ).add_network(
                id="subnet_server",
                type="slash_22",
                roles=["subnet", "subnet_server"],
                site=cluster_to_site[SERVER_CLUSTER],
            )

        # we need to add one client router + clients + relay + subnet for each client cluster
        for i, client_cluster in enumerate(CLIENT_CLUSTERS):
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
                )
                # one relay per client cluster
                .add_machine(
                    roles=["relay", f"relay_{i}"],
                    cluster=client_cluster["cluster"],
                    nodes=1,
                ).add_network(
                    id=f"subnet_client_{i}",
                    type="slash_22",
                    roles=["subnet", "subnet_client", f"subnet_client_{i}"],
                    site=cluster_to_site[client_cluster["cluster"]],
                )
            )

        # This will validate the configuration, but not reserve resources yet
        provider = en.G5k(conf)
