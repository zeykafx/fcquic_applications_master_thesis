use log::error;
use rkyv::{Archive, Deserialize, Serialize, rancor::Error};
use std::{path::Path, sync::Arc};

pub const MAX_DATAGRAM_SIZE: usize = 1350;
pub mod client_logic;

#[derive(Archive, Deserialize, Serialize, Debug, PartialEq)]
#[rkyv(compare(PartialEq), derive(Debug))]
pub struct Message {
    content: String,
    additional_data: Arc<Vec<u8>>,
    sender: String,
}

impl Message {
    pub fn new(sender: String, content: String, additional_data: Arc<Vec<u8>>) -> Self {
        Message {
            content,
            additional_data,
            sender,
        }
    }

    pub fn encode_message(&self) -> Option<Vec<u8>> {
        let bytes = match rkyv::to_bytes::<Error>(self) {
            Ok(v) => v,
            Err(e) => {
                error!("Failed to serialize message: {e:?}");
                return None;
            }
        };

        Some(bytes.into_vec())
    }

    pub fn decode_message(bytes: &[u8]) -> Option<Message> {
        let deserialized = match rkyv::from_bytes::<Message, Error>(bytes) {
            Ok(v) => v,
            Err(e) => {
                error!("Failed to deserialize message: {e:?}");
                return None;
            }
        };
        return Some(deserialized);
    }

    pub fn get_content(&self) -> String {
        self.content.clone()
    }

    pub fn get_sender(&self) -> String {
        self.sender.clone()
    }
}

pub fn get_config(is_server: bool, cert_path: String) -> quiche::Config {
    let mut config = quiche::Config::new(quiche::PROTOCOL_VERSION).unwrap();
    config.verify_peer(false); // Not prodction-ready.

    if is_server {
        config
            .load_cert_chain_from_pem_file(Path::new(&cert_path).join("cert.crt").to_str().unwrap())
            .unwrap();
        config
            .load_priv_key_from_pem_file(Path::new(&cert_path).join("cert.key").to_str().unwrap())
            .unwrap();
    }

    config
        .set_application_protos(quiche::h3::APPLICATION_PROTOCOL)
        .unwrap();

    config.set_max_idle_timeout(100_000);
    config.set_max_recv_udp_payload_size(MAX_DATAGRAM_SIZE);
    config.set_max_send_udp_payload_size(MAX_DATAGRAM_SIZE);

    let initial_max_data = 100_000_000_000;
    config.set_initial_max_data(initial_max_data);
    config.set_initial_max_stream_data_bidi_local(initial_max_data);
    config.set_initial_max_stream_data_bidi_remote(initial_max_data);
    config.set_initial_max_stream_data_uni(initial_max_data);
    config.set_initial_max_streams_bidi(initial_max_data);
    config.set_initial_max_streams_uni(initial_max_data);
    config.set_disable_active_migration(true);
    config.set_active_connection_id_limit(10);
    // config.enable_early_data();
    config.enable_pacing(false);
    config.set_cc_algorithm(quiche::CongestionControlAlgorithm::CUBIC);

    config
}

pub async fn optional_timeout(timeout: Option<std::time::Duration>) -> Option<()> {
    match timeout {
        Some(t) => {
            if t != std::time::Duration::ZERO {
                tokio::time::sleep(t).await;
            }
            Some(())
        }
        None => None,
    }
}
