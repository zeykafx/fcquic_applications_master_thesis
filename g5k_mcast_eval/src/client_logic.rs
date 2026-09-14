use std::{
    sync::Arc,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

use bytes::Bytes;
use log::{debug, error, info};

use rand::Rng;
use rand_distr::{Distribution, Exp};
use tokio_fcquiche::FcQuicMsg;

use crate::Message;

#[inline]
pub fn alloc_additional_data(
    sender: bool,
    test_mode: bool,
    additional_packet_data_size: usize,
) -> Arc<Vec<u8>> {
    // if the client is a sender and if the additional packet data size is not 0, then allocate a buffer and fill it with random data
    let additional_packet_data: Arc<Vec<u8>> = match sender && test_mode {
        true => {
            // alloc the buffer, fill it with random bytes, then put an arc on it and return that
            let mut data_vec = vec![0u8; additional_packet_data_size];
            rand::rng().fill(data_vec.as_mut_slice());
            info!("Random data in buffer: {data_vec:?}");
            Arc::new(data_vec)
        }
        false => Arc::new(Vec::new()),
    };
    additional_packet_data
}

// #[inline]
pub fn handle_sender_timeout(
    outgoing_stream_id: &mut u64,
    use_stream_id: bool,
    username: &String,
    exp: Exp<f64>,
    poisson: bool,
    send_sleep: &mut Duration,
    interval: u64,
    sent_first_ts: &mut bool,
    additional_data: Arc<Vec<u8>>,
) -> FcQuicMsg {
    debug!("Sending timestamp to server at {:?}", Instant::now());

    let msg = send_timestamp(
        false, // not using FCQUIC
        outgoing_stream_id,
        &username,
        use_stream_id,
        additional_data,
    );

    // send packet using a random interval based on the exponential distribution
    if poisson {
        let inter_pkt_time: f64 = exp.sample(&mut rand::rng());
        let pkt_interval = tokio::time::Duration::from_secs_f64(inter_pkt_time);
        debug!(
            "inter packet interval for this interval: {:?} (raw: {:.6}s)",
            pkt_interval, inter_pkt_time
        );

        // change the interval for the next packet
        *send_sleep = pkt_interval;
    } else {
        *send_sleep = tokio::time::Duration::from_millis(interval);
    }

    msg
}

// #[inline]
pub fn send_timestamp(
    is_fcquic: bool,
    outgoing_stream_id: &mut u64,
    username: &String,
    uses_stream_id: bool,
    additional_data: Arc<Vec<u8>>,
) -> FcQuicMsg {
    let start = SystemTime::now();
    let since_epoch = start
        .duration_since(UNIX_EPOCH)
        .expect("time should go forward");

    debug!("Sending timestamp to server");

    let ts_str = since_epoch.as_micros().to_string();

    let msg: FcQuicMsg;
    if let Some(encoded_msg) =
        Message::new(username.clone(), ts_str, additional_data).encode_message()
    {
        msg = FcQuicMsg::Stream((encoded_msg, true, *outgoing_stream_id));

        if uses_stream_id || is_fcquic {
            *outgoing_stream_id += 4;
        }
    } else {
        error!("Failed to encode timestamp message!");
        panic!("failed to encode timestamp message!");
    }
    msg
}

#[inline]
pub fn hex_dump(buf: &[u8]) -> String {
    let vec: Vec<String> = buf.iter().map(|b| format!("{b:02x}")).collect();

    vec.join("")
}
