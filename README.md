# Evaluating Flexicast QUIC through real-world applications

This repository contains the source code and evaluation scripts for my master thesis on Flexicast QUIC's ability to efficiently, reliably, and securely deliver application traffic for applications like a multicast chat, as well as a hierarchical architecture with relay nodes to offload ACK handling and retransmissions from an overloaded source.

## Repo structure

### Evaluations

The [evaluations/](./evaluations/) directory contains all of the test scripts, topology scripts and configurations, Grid'5000 experiments, and graph generation code.

- Local tests ([evaluations/tests/](./evaluations/tests/)): NPF test scripts, used for the multicast chat eval on many many different topologies.

- Topologies ([evaluations/topologies/](./evaluations/topologies/)): Automated network namespace topology creation scripts based on a YAML configuration file, with routers using FRRouting.
  - These scripts are based on [Anthony Doerane's work](https://github.com/Aperence/FFSexp3-master-thesis/tree/main/evaluation/topologies).

- Grid'5000 scripts ([evaluations/grid5000/](./evaluations/grid5000/)): Experiment notebooks used to run the large scale relay evaluations on Grid'5000 but also used to evaluate the multicast chat on a single server.
  - [chat_eval_single_node/](./evaluations/grid5000/chat_eval_single_node/): Notebook used for the multicast chat app eval on a single Grid'5000 server
  - [relay_eval_gre/](./evaluations/grid5000/relay_eval_gre/): Notebook used for the multisite relay eval using GRE tunnels to enable a multicast distribution tree to be created over 5 clusters.

### Submodules

- [fcquic_chat](./fcquic_chat) ([github.com/zeykafx/fcquic_chat](https://github.com/zeykafx/fcquic_chat)): Source code for the implementations of the Multicast chat application. Includes the Flexicast QUIC, baseline `quiche`, `tokio-quiche`, TCP, and TCP+TLS implementations.

- [fcquic_relay](./fcquic_relay) ([github.com/zeykafx/fcquic_relay](https://github.com/zeykafx/fcquic_relay)): Source code for implicit relay implementations. The repository contains the application relay but also the integrated relay's driver (i.e., relay binary that makes use of the integrated relay from `tokio-fcquiche`)

- [multicast-quic](./multicast-quic) ([github.com/zeykafx/flexicast-quic](https://github.com/zeykafx/flexicast-quic)): Fork of Flexicast QUIC (main source [here](https://github.com/IPNetworkingLab/flexicast-quic)) that contains the integrated relay code and other modifications made during this work
