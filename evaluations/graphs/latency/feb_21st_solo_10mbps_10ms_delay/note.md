# important

FCQUIC removed the sender for most of the runs, therefore FCQUIC had very few samples compared to the other implementations...

```
Additional data = 0 bytes:
Baseline QUIC samples: 0
Baseline TCP samples: 268
Baseline TCP (NO TLS) samples: 242
FC-QUIC samples: 31
FC-QUIC with FEC samples: 0
Tokio-quiche samples: 357

---

Additional data = 500 bytes:
Baseline QUIC samples: 0
Baseline TCP samples: 304
Baseline TCP (NO TLS) samples: 276
FC-QUIC samples: 32
FC-QUIC with FEC samples: 0
Tokio-quiche samples: 270

---

Additional data = 1100 bytes:
Baseline TCP samples: 187
Baseline TCP (NO TLS) samples: 204
FC-QUIC samples: 154
Tokio-quiche samples: 287
```