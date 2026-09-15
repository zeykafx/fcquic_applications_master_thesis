use log::error;
use rkyv::{Archive, Deserialize, Serialize, rancor::Error};
use std::sync::Arc;

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
