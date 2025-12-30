# Evaluating Flexicast QUIC through real-world applications

## Diectories

- [Evaluations](./evaluations):
  - [Latency Test](./evaluations/tests/latency): Test of the latency under varying levels of loss for FCQUIC, QUIC, and TCP.  
  - [Receivers Test](./evaluations/tests/receivers): Test of the latency with increasing numbers of receivers for FCQUIC, QUIC, and TCP.  
  - [Topology scripts](./evaluations/topologies): Set of scripts that parse a yaml file and starts a virtual network in netwok namespaces (uses FRRouting) 
<!--- [fcquic_chat](./fcquic_chat):
  - [FCQUIC Chat Application](./fcquic_chat/src): [client.rs](./fcquic_chat/src/client.rs) and [server.rs](./fcquic_chat/src/server.rs)
  - [Baseline QUIC Chat Application](./fcquic_chat/src): [quic-client.rs](./fcquic_chat/src/quic-client.rs) and [quic-server.rs](./fcquic_chat/src/quic-server.rs)
  - [Baseline TCP (with TLS) Chat Application](./fcquic_chat/src): [tcp-client.rs](./fcquic_chat/src/tcp-client.rs) and [tcp-server.rs](./fcquic_chat/src/tcp-server.rs)-->
<!--- [multicast-quic](./multicast-quic): Multicast QUIC repository-->
