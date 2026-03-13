# NOTE: Dockerfile was originally from Anthony Doeraene (https://github.com/Aperence/FFSexp3-master-thesis/blob/main/dockerfiles/host/Dockerfile)
# it was modified to use debian:bookworm-slim instead of fedora

FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git gcc g++ cmake clang make ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# copy both dirs but without the target dir
COPY --exclude=*target* ./fcquic_chat /fcquic_chat
COPY --exclude=*target* ./multicast-quic /multicast-quic
# compile everything
RUN cd fcquic_chat && CARGO_NET_GIT_FETCH_WITH_CLI=true cargo build --release

# runtime section, only keep the binaries and certs
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /fcquic_chat/target/release/client  /
COPY --from=builder /fcquic_chat/target/release/tquic-client  /
COPY --from=builder /fcquic_chat/target/release/tcp-client  /
COPY --from=builder /fcquic_chat/target/release/server  /
COPY --from=builder /fcquic_chat/target/release/tquic-server  /
COPY --from=builder /fcquic_chat/target/release/tcp-server  /
COPY --from=builder /fcquic_chat/cert.crt /
COPY --from=builder /fcquic_chat/cert.key /
