use clap::Parser;
use g5k_mcast_eval::Message;
use log::{debug, info};
use netaddr2::{Contains, Netv4Addr};
use quiche::flexicast::McConfig;
use std::net::{Ipv4Addr, SocketAddr};
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tokio::sync::mpsc;
use tokio_fcquiche::FcQuicMsg;
use tokio_fcquiche::io::receiver::TokioFcQuicRecv;

const MAX_DATAGRAM_SIZE: usize = 1350;

#[derive(Parser)]
struct Args {
    /// Activate flexicast extension.
    #[clap(long)]
    flexicast: bool,

    /// server address
    #[clap(long = "server-ip", value_parser)]
    server_ip: Ipv4Addr,

    /// server or relay's port
    #[clap(long = "port", value_parser)]
    port: u16,

    // /// URL of the server to contact.
    // url: url::Url,
    /// Multicast local IP.
    #[clap(short = 'l', long = "local", default_value = "0.0.0.0", value_parser)]
    local_ip: Ipv4Addr,

    /// Multicast packets are proxied using packet replication for this client.
    /// This argument is a trick to avoid out-of-band computation by the source
    /// of the proxies to the clients. If this value is true, instead of
    /// binding to the flexicast address given in the MC_ANNOUNCE frame, the
    /// client will listen to its own address and the port advertised by the
    /// source.
    #[clap(long = "proxy")]
    proxy_uc: bool,

    /// Sets the initial flow control limits on the receiver.
    /// If this parameter is not set, the receiver uses unlimited flow control.
    #[clap(long = "flow-control")]
    initial_flow_control: Option<u64>,

    /// Username for chat messages
    #[clap(short = 'u', long = "username", default_value = "Client")]
    username: String,

    /// ------ Test arguments ------

    /// Duration of the test in seconds
    #[clap(long = "length", default_value = "30")]
    length: u64,

    /// Boolean that defines if this client will automatically send timestamps
    #[clap(long = "sender")]
    sender: bool,

    /// when enabled, allow the receiver to receive FEC information
    #[clap(long = "fec")]
    fec: bool,

    /// Size of the additional data that will be sent in the messages that the sender emits
    #[clap(long = "additional-data-size", default_value = "1000")]
    additional_packet_data_size: usize,

    /// Congestion control algorithm to use
    #[clap(long = "cc-algorithm", default_value = "cubic")]
    cc_algorithm: quiche::CongestionControlAlgorithm,

    /// cluster names
    #[clap(long = "cluster-names", value_parser)]
    cluster_names: Vec<String>,

    /// subnets for each of the clusters
    #[clap(long = "cluster-subnets", value_parser)]
    cluster_subnets: Vec<Ipv4Addr>,

    /// EPOCH timestamp of the test start, typically in the future by a few seconds
    #[clap(long = "test-start-ts")]
    test_start_ts: f64,

    /// whether or not to output the results with the cluster name to enable
    #[clap(long = "per-cluster-results")]
    per_cluster_results: bool,
}

#[tokio::main(flavor = "current_thread")]
// #[tokio::main(flavor = "multi_thread", worker_threads = 2)]
async fn main() {
    env_logger::builder().format_timestamp_nanos().init();
    let args = Args::parse();

    // figure out which cluster this client is located in, this way we can log results per clusters
    let local_ip = args.local_ip;

    let subnet_netmask = Ipv4Addr::new(255, 255, 252, 0); // /22 subnet

    // we can figure out which cluster this client belongs to by figuring out the
    // subnet it belongs to, using the same approach as for finding the relay ip
    let mut cluster_name: Option<String> = None;
    // zip together the names and subnets. They were split in two args because idk how to pass in maps as arguments, let alone how to create maps in bash...
    for (subnet_ip, name) in args.cluster_subnets.iter().zip(args.cluster_names.iter()) {
        let netaddr = Netv4Addr::new(*subnet_ip, subnet_netmask);
        if netaddr.contains(&local_ip) {
            cluster_name = Some(name.clone());
            info!("client ip contained in {}, cluster: {}", netaddr, name);
            break;
        }
    }
    if let Some(ref name) = cluster_name {
        info!("Client is in cluster: {}", name);
    } else {
        info!("Couldn't find client's cluster");
    }

    let (tx_app, rx_app) = mpsc::channel(10_000);

    // Create the Flexicast Quiche tokio receiver.
    let peer_addr = SocketAddr::new(args.server_ip.into(), args.port);

    let config = get_config(&args);
    let (mut tfc_recv, mut rx_app_fcquiche) = TokioFcQuicRecv::new(
        peer_addr,
        config,
        args.local_ip,
        args.flexicast,
        args.proxy_uc,
        rx_app,
        None,
        false,
    );

    let username = args.username;
    debug!(
        "Running in test mode as {}, (sender: {})",
        username.clone(),
        args.sender
    );

    tokio::spawn(async move {
        debug!("Starting main loop");

        // if the client is a sender and if the additional packet data size is not 0, then allocate a buffer and fill it with random data
        // let additional_packet_data =
        //     alloc_additional_data(args.sender, true, args.additional_packet_data_size);

        // // sleep for a few seconds to let the connection go through
        // tokio::time::sleep(tokio::time::Duration::from_secs(
        //     1,
        // ))
        // .await;

        // let mut outgoing_stream_id = 2;

        // the test_start_ts argument is an EPOCH timestamp of when the test should start, this is typically 5 seconds in the future
        let test_start = UNIX_EPOCH + Duration::from_secs_f64(args.test_start_ts);
        let now = SystemTime::now();

        match test_start.duration_since(now) {
            Ok(remaining) => {
                println!("Sleeping {}s until test start", remaining.as_secs_f64(),);
                tokio::time::sleep(remaining).await;
                println!("Finished sleeping, starting test");
            }
            Err(_) => {
                log::error!("The test start is in the past");
                println!("Test start is in the past");
            }
        }

        let test_deadline =
            tokio::time::Instant::now() + tokio::time::Duration::from_secs(args.length);
        let test_deadline_sleep = tokio::time::sleep_until(test_deadline);
        tokio::pin!(test_deadline_sleep);

        // Create interval for test mode sender
        let send_sleep = std::time::Duration::from_secs_f64(1.0);
        let send_sleep_instant = tokio::time::Instant::now() + send_sleep;
        let send_timer = tokio::time::sleep_until(send_sleep_instant);
        tokio::pin!(send_timer);

        let mut batch: Vec<FcQuicMsg> = Vec::with_capacity(10);
        let mut should_break = false;

        let cluster_name_local = cluster_name.clone();
        let username_local = username.clone();

        loop {
            tokio::select! {

                // read from the rx channel for incoming messages from the server
                n = rx_app_fcquiche.recv_many(&mut batch, 10) => {
                    if n == 0 {
                        break;
                    }
                    for recv_msg in batch.drain(..) {
                        match recv_msg {
                            FcQuicMsg::Close => {
                                debug!("Received close stream");
                                rx_app_fcquiche.close();
                                println!("Server sent a close message, stopping...");
                                should_break = true;
                                break;
                            }
                            FcQuicMsg::Stream((data, fin, recv_stream_id)) => {
                                if let Some(decoded) = Message::decode_message(&data) {

                                    // parse the received value as a u128
                                    let received_timestamp: u128 = decoded
                                        .get_content()
                                        .parse()
                                        .expect("Failed to parse timestamp");


                                    let now = SystemTime::now()
                                        .duration_since(UNIX_EPOCH)
                                        .expect("time should go forward")
                                        .as_micros();

                                    let latency = now.saturating_sub(received_timestamp);

                                    // TODO: add more metrics here!
                                    if decoded.get_sender() != username  {
                                        match args.per_cluster_results {
                                            true => {

                                                println!(
                                                    "RESULT-LATENCY-{} {}",
                                                    match cluster_name_local.as_ref() {
                                                        Some(name) => name.as_str(),
                                                        None => username_local.as_str(),
                                                    },
                                                    latency,
                                                );
                                            },
                                            false => {
                                                println!(
                                                    "RESULT-LATENCY {}",
                                                    latency,
                                                );

                                            }
                                        };
                                    }

                                } else {
                                    log::warn!("Failed to decode received message");
                                    println!("Failed to decode received message");
                                }

                                if fin {
                                    log::trace!("Stream {} finished", recv_stream_id);
                                }

                            },
                            _ => ()
                        }
                    }
                    if should_break {
                        break;
                    }
                },
                // only send timestamps when in test mode and this client is a sender
                // () = &mut send_timer, if args.sender => {
                //     debug!("Sending timestamp to server at {:?}", Instant::now());

                //     let fc_msg = send_timestamp(
                //         true,
                //         &mut outgoing_stream_id,
                //         &username,
                //         true,
                //         additional_packet_data.clone(),
                //     );

                //     tx_app.send(fc_msg).await.expect("Failed to send to fcquic server");


                // },
                () = &mut test_deadline_sleep => {
                    println!("Test finished, closing connection....");
                    debug!("Test finished, closing connection");

                    if let Err(e) = tx_app.send(FcQuicMsg::Close).await {
                        debug!("failed to send Close message: {:?}", e);
                    }

                    rx_app_fcquiche.close();
                    break;
                },
                _ = tokio::signal::ctrl_c() => {
                    println!("Closing connection....");
                    debug!("Sending Close message");

                    if let Err(e) = tx_app.send(FcQuicMsg::Close).await {
                        debug!("failed to send Close message: {:?}", e);
                    }

                    rx_app_fcquiche.close();
                    break;
                }
            }
        }
    });

    // Start the Flexicast QUIC receiver.
    tfc_recv.run().await.unwrap();

    debug!("Client disconnected.");
    println!("Client disconnected.");

    // force exit
    std::process::exit(0);
}

fn get_config(args: &Args) -> quiche::Config {
    let mut config = quiche::Config::new(quiche::PROTOCOL_VERSION).unwrap();
    config.verify_peer(false); // Not prodction-ready.

    config
        .set_application_protos(quiche::h3::APPLICATION_PROTOCOL)
        .unwrap();

    if !args.flexicast {
        config.set_max_idle_timeout(100_000);
    }
    config.set_max_recv_udp_payload_size(MAX_DATAGRAM_SIZE);
    config.set_max_send_udp_payload_size(MAX_DATAGRAM_SIZE);

    let initial_max_data = match args.initial_flow_control {
        Some(v) => v,
        None => 100_000_000_000,
    };
    config.set_initial_max_data(initial_max_data);
    config.set_initial_max_stream_data_bidi_local(initial_max_data);
    config.set_initial_max_stream_data_bidi_remote(initial_max_data);
    config.set_initial_max_stream_data_uni(initial_max_data);
    config.set_initial_max_streams_bidi(initial_max_data);
    config.set_initial_max_streams_uni(initial_max_data);
    config.set_active_connection_id_limit(10);
    config.enable_pacing(false);
    config.set_cc_algorithm(args.cc_algorithm);

    if args.flexicast {
        config.set_initial_max_path_id(10);
        config.set_enable_flexicast(args.flexicast);
        config.set_recv_fec(true);
    }

    config
}
