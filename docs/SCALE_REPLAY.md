# Scale and replay checkpoint

**Status:** short nontraining reference benchmarks completed on this Windows host. A large fly graph has not been loaded or timed. The current CPU model is a correctness reference, not an overnight full-connectome training backend.

The host exposed 6 physical / 12 logical CPU cores, about 16 GiB total RAM and about 6 GiB available at inspection. [`benchmark_reference.py`](../scripts/benchmark_reference.py) built synthetic ring graphs with eight outgoing edges per neuron and simulated 50 one-millisecond ticks with 1% of neurons externally driven. The measurements include per-tick snapshots and are not a forecast for BANC's far denser edge set.

| Neurons | Edges | Wall seconds per simulated second | RSS after simulation | Peak queued arrivals |
| ---: | ---: | ---: | ---: | ---: |
| 1,000 | 8,000 | 1.48 | 25 MiB | 80 |
| 10,000 | 80,000 | 14.79 | 36 MiB | 800 |
| 100,000 | 800,000 | 153.85 | 138 MiB | 8,000 |

Raw records: [`1k`](figures/benchmark_1000.json), [`10k`](figures/benchmark_10000.json), [`100k`](figures/benchmark_100000.json). The 100k result is based on 50 ms of simulated time, so longer-running activity and queue behavior remain unknown. The reference visits every neuron every tick and allocates a snapshot for each requested step. Sparse CSR storage avoids an N×N matrix but does not make the current Python tick loop fast enough for an unmeasured full-graph six-hour training claim.

`TinyLaneSession` already roundtrips complete coupled state through **trusted, same-version pickle** in an automated mid-map replay test. It is not a portable, versioned checkpoint and must not load untrusted bytes. The proposed overnight synthetic study therefore writes atomic progress files after each short seed/condition run and can resume at those boundaries. A crash during one trial may repeat that trial; it cannot silently skip it. This operational restart strategy does not satisfy a future large-connectome checkpoint contract.

Before full graph simulation, benchmark the actual selected edge table at multiple subgraph sizes, including active spikes, delayed arrivals, masked plasticity, memory peak, queue growth, and selective logging. Any compiled/active-set backend must match the reference's model-level spike, arrival and plasticity tests and disclose numerical differences. Keep source graph, neuron state, edge state, plasticity state and scheduler state separate; no dense adjacency rewrite is needed.
