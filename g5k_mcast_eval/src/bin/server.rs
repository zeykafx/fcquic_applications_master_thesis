use clap::Parser;
use g5k_mcast_eval::Message;
use g5k_mcast_eval::client_logic::alloc_additional_data;
use log::debug;
use log::error;
use log::info;
use quiche::fec::schedulers::FecSchedulerAlgorithm;
use quiche::flexicast::FcConfig;
use quiche::flexicast::McConfig;
use quiche::flexicast::cca::FcFlowCwnd;
use std::net;
use std::path::Path;
use std::time;
use std::time::Duration;
use std::time::Instant;
use std::time::SystemTime;
use std::time::UNIX_EPOCH;
use tokio_fcquiche::FcQuicMsg;
use tokio_fcquiche::io::TokioFcQuic;
use tokio_fcquiche::io::TokioFcQuicConfig;

#[derive(Parser)]
struct Args {
    /// Activate flexicast extension.
    #[clap(long)]
    flexicast: bool,

    /// Keylog file for flexicast channel.
    #[clap(long = "keylog", value_parser, default_value = "/tmp/fc-server.txt")]
    fc_keylog_file: String,

    /// Source address of the server.
    #[clap(long = "src", default_value = "127.0.0.1:4433")]
    src_addr: net::SocketAddr,

    /// Certificate path.
    #[clap(long = "cert-path", value_parser, default_value = ".")]
    cert_path: String,

    /// Multicast address.
    #[clap(long = "mc-addr", value_parser, default_value = "239.239.239.35:4434")]
    mc_addr: net::SocketAddr,

    /// Multicast source address.
    /// Must be different from the source address.
    #[clap(long = "mc-src-addr", value_parser, default_value = "127.0.0.1:4443")]
    mc_src_addr: net::SocketAddr,

    /// Flexicast flow timer.
    #[clap(long, value_parser, default_value = "0")]
    fc_timer: u64,

    /// Specify the congestion window for the flexicast flow.
    /// The possible values are:
    /// - A string value representing a congestion control algorithm;
    /// - An integer value representing the fixed congestion window;
    /// - The 'disabled' string, representing an unlimited congestion window.
    #[clap(long = "fc-cwnd", default_value = "cubic")]
    fc_cwnd: FcFlowCwnd,

    /// Number of clients to listen before actually sending data to the wire.
    #[clap(long = "wait", value_parser)]
    wait: Option<u64>,

    /// Whether the application allows unicast delivery instead of flexicast.
    #[clap(long = "unicast")]
    allow_unicast: bool,

    /// Whether the unicast path has unlimited congestion window.
    #[clap(long = "unicast-unlimited-cwnd")]
    uc_unlimited_cwnd: bool,

    /// Whether the flexicast flow must be created using path probing.
    #[clap(long = "probe-path")]
    probe_path: bool,

    /// Unicast fall-back delay for the scheduler, in ms.
    #[clap(long = "fall-back-delay", value_parser)]
    fall_back_delay: Option<u64>,

    /// Whether to use `sendmmsg` instead of relying on real flexicast
    /// to distribute data on the flexicast flow.
    /// The value is the number of instances of sendmmsg to use.
    /// For now, creates 'sendmmsg' instances for each flexicast flow.
    #[clap(long = "sendmmsg", value_parser)]
    sendmmsg: Option<u64>,

    /// Sets the initial flow control for the flexicast flow.
    #[clap(long = "initial-fc-flow")]
    initial_fc_flow: Option<u64>,

    /// Whether to use FEC for flexicast.
    /// If set, defines the FEC scheduler to use.
    #[clap(long = "fec-scheduler")]
    fec_scheduler: Option<FecSchedulerAlgorithm>,

    /// Number of leaf controllers to use.
    #[clap(long = "nb-controllers", default_value = "1")]
    nb_controllers: u64,

    /// Test mode boolean, if true print less things,...
    #[clap(long = "test-mode")]
    test_mode: bool,

    /// Duration of the test in seconds
    #[clap(long = "length", default_value = "30")]
    length: u64,

    /// Congestion algorithm to use
    #[clap(long = "cc-algorithm", default_value = "cubic")]
    cc_algorithm: quiche::CongestionControlAlgorithm,

    /// EPOCH timestamp of the test start, typically in the future by a few seconds
    #[clap(long = "test-start-ts")]
    test_start_ts: f64,

    /// Size of the additional data that will be sent in the messages that the sender emits
    #[clap(long = "additional-data-size", default_value = "1000")]
    additional_packet_data_size: usize,
}

#[tokio::main(flavor = "multi_thread", worker_threads = 8)]
// #[tokio::main(flavor = "multi_thread", worker_threads = 2)]
async fn main() {
    env_logger::builder().format_timestamp_nanos().init();
    let args = Args::parse();

    // Create Flexicast Quiche tokio config.
    let fc_quic_tokio_config = TokioFcQuicConfig {
        unicast: args.allow_unicast,
        unicast_unlimited_cwnd: args.uc_unlimited_cwnd,
        sendmmsg: args.sendmmsg,
        wait: args.wait,
        flexicast: args.flexicast,
        fc_keylog_file: args.fc_keylog_file.clone(),
        fallback_delay: args.fall_back_delay.map(|d| time::Duration::from_millis(d)),
        uc_src_addr: args.src_addr,
        nb_leaf_controllers: args.nb_controllers,
        h3_config: None,
        is_relay: false,
    };

    // Transmission channel towards the application, supposed to be unique because
    // the receivers may send messages without knowing to which flexicast flow it
    // belongs.
    let (tx_app, rx_app) = tokio::sync::mpsc::channel(10_000);

    let mut fcquiche = TokioFcQuic::new(fc_quic_tokio_config, tx_app);

    // create a single fc flow
    let flow_config = FcConfig {
        fc_tp: args.flexicast,
        probe_mc_path: false,
        max_data: args.initial_fc_flow.unwrap_or(1_000_000),
        max_stream_data: args.initial_fc_flow.unwrap_or(1_000_000),
        fc_timer: args.fc_timer,
        fec: args.fec_scheduler.is_some(),
        fec_scheduler: args
            .fec_scheduler
            .unwrap_or(FecSchedulerAlgorithm::NoRedundancy),
        src_addr: args.mc_src_addr,
        mc_addr: args.mc_addr,
        crt_path: args.cert_path.clone(),
        fc_cca: args.fc_cwnd,
        ..Default::default()
    };

    // Creates a new flexicast flow according to flow_config
    fcquiche
        .add_fc_flow(flow_config, &args.fc_keylog_file)
        .await
        .unwrap();

    // get the transmission channel to send app content
    let tx_fc = fcquiche.get_tx_fc_flow(0).unwrap();

    let uc_config = get_config(&args);

    // The stream id for the flexicat flow starts as 0x3 because it has "0b11" as the least significant bits
    // This tells quic that the stream is a unidirectional server-initiated stream
    // We'll then increment by 4 in order to get the next number with those same LSBs.
    let mut fc_flow_stream_id = 3;

    tokio::spawn(async move {
        debug!("Starting message handling loop");
        let mut rx_app = rx_app;

        let additional_packet_data =
            alloc_additional_data(true, true, args.additional_packet_data_size);

        // the test_start_ts argument is an EPOCH timestamp of when the test should start, this is typically 5 seconds in the future
        // NOTE: the server adds 1 seconds
        let test_start = UNIX_EPOCH + Duration::from_secs_f64(args.test_start_ts + 1.0);
        let now = SystemTime::now();

        let send_sleep = test_start
            .duration_since(now)
            .expect("Test start should be in the future");
        let send_sleep_instant = tokio::time::Instant::now() + send_sleep;
        let send_timer = tokio::time::sleep_until(send_sleep_instant);
        tokio::pin!(send_timer);
        let mut sent_msg: bool = false;

        let test_deadline =
            tokio::time::Instant::now() + tokio::time::Duration::from_secs(args.length);
        let test_deadline_sleep = tokio::time::sleep_until(test_deadline);
        tokio::pin!(test_deadline_sleep);

        let mut batch: Vec<FcQuicMsg> = Vec::with_capacity(100);
        loop {
            tokio::select! {
                n = rx_app.recv_many(&mut batch, 100) => {
                    if n == 0 {
                        break;
                    }
                    // read messages from unicast receiver
                    for msg in batch.drain(..) {
                        match msg {
                            FcQuicMsg::Close => {
                                debug!("Received close");
                            }

                            FcQuicMsg::Stream((data, _fin, _)) => {

                                // create a new stream frame with the current stream used on the fc flow
                                let fc_msg = FcQuicMsg::Stream((data, true, fc_flow_stream_id));
                                fc_flow_stream_id += 4;

                                // send the message to the flexicast flow
                                if let Err(e) = tx_fc.send(fc_msg).await {
                                    log::error!("Failed to send message to flexicast flow: {:?}", e);
                                    return;
                                }

                                info!("Server just sent on the fc flow a message received on a uc path",);
                            }
                            _ => (),
                        }
                    }
                },
                () = &mut send_timer, if !sent_msg => {

                    info!("Sending msg to all clients at {:?}", Instant::now());

                    let start = SystemTime::now();
                    let since_epoch = start
                        .duration_since(UNIX_EPOCH)
                        .expect("time should go forward");

                    debug!("Sending timestamp to clients");

                    let ts_str = since_epoch.as_micros().to_string();

                    if let Some(encoded_msg) = Message::new("Source".into(), ts_str, additional_packet_data.clone()).encode_message() {

                        // create a new stream frame with the current stream used on the fc flow
                        let fc_msg = FcQuicMsg::Stream((encoded_msg, true, fc_flow_stream_id));
                        fc_flow_stream_id += 4;

                        // send the message to the flexicast flow
                        if let Err(e) = tx_fc.send(fc_msg).await {
                            log::error!("Failed to send message to flexicast flow: {:?}", e);
                            return;
                        }
                        info!("Sent msg to all clients on the MC Flow");
                        sent_msg = true;

                    } else {
                        error!("Failed to encode timestamp message!");
                        panic!("failed to encode timestamp message!");
                    }

                },
                () = &mut test_deadline_sleep, if args.test_mode => {

                    println!("Test finished, closing connection....");
                    debug!("Test finished, closing connection");

                    if let Err(e) = tx_fc.send(FcQuicMsg::Close).await {
                        debug!("failed to send Close message: {:?}", e);
                    }

                    rx_app.close();

                    debug!("Server stopped");
                    println!("Server stopped");

                    std::process::exit(0);

                },
            }
        }
    });

    // run tokio-fcquiche in its own thread
    fcquiche.run(uc_config).await.unwrap();

    debug!("Server stopped");
    println!("Server stopped");

    // force exit
    std::process::exit(0);
}

fn get_config(args: &Args) -> quiche::Config {
    let mut config = quiche::Config::new(quiche::PROTOCOL_VERSION).unwrap();

    config
        .load_cert_chain_from_pem_file(
            Path::new(&args.cert_path)
                .join("cert.crt")
                .to_str()
                .unwrap(),
        )
        .unwrap();
    config
        .load_priv_key_from_pem_file(
            Path::new(&args.cert_path)
                .join("cert.key")
                .to_str()
                .unwrap(),
        )
        .unwrap();

    config
        .set_application_protos(quiche::h3::APPLICATION_PROTOCOL)
        .unwrap();

    config.set_max_recv_udp_payload_size(tokio_fcquiche::MAX_DATAGRAM_SIZE);
    config.set_max_send_udp_payload_size(tokio_fcquiche::MAX_DATAGRAM_SIZE);

    let initial_max_data = match args.initial_fc_flow {
        Some(v) => v,
        None => 100_000_000_000,
    };

    config.set_initial_max_data(initial_max_data);
    config.set_initial_max_stream_data_bidi_local(initial_max_data);
    config.set_initial_max_stream_data_bidi_remote(initial_max_data);
    config.set_initial_max_stream_data_uni(initial_max_data);
    config.set_initial_max_streams_bidi(initial_max_data);
    config.set_initial_max_streams_uni(initial_max_data);
    config.set_disable_active_migration(true);
    config.set_active_connection_id_limit(10);
    config.enable_pacing(false);
    config.set_send_fec(false);
    config.set_recv_fec(false);
    config.set_enable_flexicast(args.flexicast);
    config.set_initial_max_path_id(10);
    config.set_cc_algorithm(args.cc_algorithm);

    config
}
