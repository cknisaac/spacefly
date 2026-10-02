# Larval L2 effect-scale evidence gate

**Review date:** 2026-10-02  
**Decision:** **INCONCLUSIVE — no independent quantitative parameter range transfers to this exact L2 pathway**  
**Scope:** Read-only audit of primary larval physiology and relevant adjacent electrophysiology. No model, simulation, or tuning was performed.

## Frozen state checked

Current SHA-256 values for the relevant frozen artifacts:

| Artifact | SHA-256 |
|---|---|
| L2 first-instar subgraph manifest | `84fb7af5160a405a072170466ea19e134cd12bc61ed1a7c565f301972da07c89` |
| Signed downstream model v2 | `9b017e0df5a3d9e71e6224ba1c2c35343dee67cbf50a45fff62ab0ae88c1301c` |
| Context subgraph manifest v3 | `97560028444a02c8bb0c68c6608fd68dcfc5c103276b67debd30b059d0f6003b` |
| Context electrical model v3 | `c5f9adcf02378ded60ad66f11f8e1e03738955b94a1ab0a1089cc99b3033f60e` |
| v3 context probe result (frozen FAIL) | `54decac4309faa697d11666ad6a6a4d30c9c381146bbdd7e060d573bbb2c5a4f` |

V2 holds the measured topology and LIF/contact values while constraining the two downstream signs by reported functional effect classes. V3 adds the anatomically measured noci-second-order-PN→Ipsigoro inputs, but reuses assumed pulse and contact scales. The v3 fail means those frozen values do not activate Ipsigoro or Goro; it does **not** show that the biological signal cannot do so.

For reference, v3 uses 1 nF, 10 MΩ, 10 ms membrane time constant, 5 ms synaptic time constant, a 1 mV threshold, 0.01 mV-equivalent per anatomical contact, 2 ms delay, 12 mV-equivalent 5 ms sensory/context pulses, and one Goro spike as its action event. The model itself labels these as engineering assumptions or overlays. The audit found no primary measurement that independently bounds these values for the listed cells and edges.

## Evidence by required parameter

| Target | Primary evidence found | Quantitative meaning and transfer limits | Gate |
|---|---|---|---|
| **KC→MBON-d1 efficacy and excitability** | Jones (2024) reports larval MBON-d1 functional activation experiments and connectomic inputs; Eschbach et al. (2021) report odor-evoked calcium responses in larval MBON-m1 after conditioning. | The reviewed larval studies do not provide unitary KC→MBON-d1 synaptic currents, PSPs, conductance, delay, or a calibrated KC pulse-to-MBON transfer curve. MBON-m1 calcium response is a different output cell/compartment and is not an electrical scale for MBON-d1. L1 contact counts are anatomy, not efficacy. | **INCONCLUSIVE** |
| **Noci second-order PN→Ipsigoro** | The S1 connectome records 4 and 7 contacts from annotated nociceptive second-order PN IDs to Ipsigoro. Jones (2024, Ch. 5) finds MD-IV nociceptor activation increases Ipsigoro calcium and Ipsigoro inactivation reduces MD-IV-evoked rolling. | This supports a net functional nociceptive route and direction, but the manipulated MD-IV→Ipsigoro route is not a calibrated measurement of the two exact S1 PN→Ipsigoro edges. ΔF/F is a calcium indicator response, not mV, pA, conductance, or spike threshold. No edge efficacy or input-to-PN electrical transfer range follows. | **INCONCLUSIVE** |
| **MBON-d1→Ipsigoro** | Jones (2024, Ch. 6, Fig. 6.1) reports that optogenetic activation of MBON-d1 significantly lowers Ipsigoro ΔF/F (N=6); the thesis identifies the effect as inhibitory. | This is direct, third-instar, exact-cell-pair functional evidence for the **net effect class**. The output is calcium fluorescence during population optogenetic activation; it does not isolate a unitary edge or calibrate current, voltage, conductance, latency, or the relation between anatomical contacts and electrical weight. It supports a negative signed abstraction, not its numerical magnitude. | **INCONCLUSIVE** |
| **Ipsigoro→Goro** | Jones (2024, Ch. 4, Fig. 4.3) reports increased Goro ΔF/F during optogenetic Ipsigoro activation (N=8) and context-dependent rolling promotion. | Exact-cell-pair, third-instar evidence supports a positive functional effect class. It is not a unitary synaptic current/voltage measurement, nor a transfer curve giving the Ipsigoro activity needed to evoke a Goro spike. Behavior required noxious context; one simulated spike is not established as the biological action threshold. | **INCONCLUSIVE** |
| **Goro excitability and spike/action criterion** | Ohyama et al. (2015) establish Goro as a command-like neuron in nociceptive rolling; Jones (2024) records Goro calcium responses to optogenetic inputs and behavior. | These establish behavioral relevance and calcium modulation, but the reviewed work supplies no exact Goro resting potential, input resistance, capacitance, rheobase, voltage threshold, or spike count/latency boundary that predicts rolling. The simulator's “≥1 spike in 100 ms” is an engineering readout, not a physiologically calibrated threshold. | **INCONCLUSIVE** |

## Adjacent electrophysiology is not transferable

- **Larval motoneurons:** Huber et al. (2009) measured third-instar motor-neuron properties during optogenetic activation; reported resting potential around −51 to −52 mV and input resistance around 1.1 GΩ. Those numbers describe identified motor neurons, not KCs, MBON-d1, Ipsigoro, Goro, or the relevant synapses. They cannot set those cells' LIF parameters.
- **Larval VNC second-order neurons:** primary patch-clamp studies (including *Cross-modal modulation gates nociceptive inputs in Drosophila*, 2023) show that some larval SONs are spiking and report electrophysiological methods and cell-specific results. The patched A08n/Basin/Wave population is not the exact S1 noci-second-order PN identities projecting to Ipsigoro, and it does not calibrate PN→Ipsigoro efficacy.
- **Adult mushroom-body neurons:** identified adult MBON/KC patch-clamp data provide absolute voltages and current-injection responses in some cell classes (for example adult MBON-α3 resting potential and current-step responses in *The cellular architecture of memory modules in Drosophila supports stochastic input integration*, 2023). These are different developmental stage and cells. Current injected at the soma is not a synaptic weight at larval KC→MBON-d1.
- **Generic connectome simulations:** published fly-wide LIF parameterizations set shared resting/threshold/time-constant values from literature-wide estimates and explicitly describe them as assumptions. A modeling convention is not an independent physiological range for these exact larval cell types.

Thus, there are absolute neural electrical values in adjacent Drosophila preparations, but no justified transfer interval for any central L2 scale asked for here. Qualitative calcium direction, behavioral necessity/sufficiency, cell-class voltage values, and contact counts should not be converted into the simulator's millivolt-per-contact or threshold values.

## Decision and next discriminating evidence

**INCONCLUSIVE.** No reviewed primary source directly shows that the proposed L2 signals cannot drive the downstream cells, so a biological FAIL is not supported. The reviewed evidence does support selected effect directions and behavioral context, but it does not bound the edge efficacy, membrane parameters, delay, sensory encoding amplitude, or Goro spike criterion for the exact path. A fresh gain/threshold sweep would therefore still be outcome-based tuning, even if the sweep is called a sensitivity analysis.

### Targeted literature recheck (2026-10-02)

A targeted search for exact larval MBON-d1, Ipsigoro, and Goro electrophysiology found quantitative intracellular recordings from superficial larval VNC neurons, primarily identified motor neurons, but no measurements from this L2 MB pathway. [Rohrbough & Broadie (2002)](https://doi.org/10.1152/jn.2002.88.2.847) report −50 to −60 mV resting potentials and current-injection responses in those VNC cells; these do not transfer to MBON-d1 or the exact Ipsigoro/Goro cells. Adult MBON/KC electrophysiology likewise cannot set larval L2 parameters. This recheck confirms the existing INCONCLUSIVE gate; it does not create a biological FAIL or authorize new simulator scales.

### Connectome-model parameter audit (2026-10-02)

Two broader connectome-based models were also checked as possible sources of reusable values. Shiu et al.'s adult whole-brain model explicitly estimates/inferentially assigns membrane and synapse parameters and leaves a global synaptic scale as a free modeling parameter; it is an adult model and does not provide an L2 cell-specific calibration. The 2026 larval olfactory-pathway SNN from Watts & Webb uses the Winding connectome and includes ORN→KC→APL, but its documented output is a decoder rather than the L2 MBON-d1→Ipsigoro→Goro path; it learns 449 scalar biophysical parameters and does not report exact L2 synaptic measurements. Its trained decoder is not usable for this goal, and its learned constants cannot be treated as measurements. [Shiu et al. (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11446845/); [Watts & Webb (CCN 2026 code/paper record)](https://github.com/InsectRobotics/connectome_emergence).

Keep the v2 and v3 failures frozen. Do not use the L2 circuit for learning or retune it to pass. An evidence-based quantitative gate would require direct larval recordings from the identified KC/MBON-d1, Ipsigoro, and Goro cells (and identified noci-second-order PN inputs), with calibrated current/voltage responses or synaptic currents and a Goro spike-to-behavior relationship; alternatively, a primary paper may provide those exact-cell measurements. Until then, L2 cannot advance on electrical-scale evidence.

## Primary sources

- Jones, B. M. W. (2024). *Circuit Mechanisms of Context-dependent Memory-based Action Selection*. University of Cambridge PhD thesis, especially Chs. 4–6, Figs. 4.3, 5.2, 6.1–6.2. [Repository PDF](https://api.repository.cam.ac.uk/server/api/core/bitstreams/737cafca-8765-40b0-869e-a7756817d803/content). The methods define ΔF/F as `(F−F0)/F0` and analyze fluorescence change, not voltage or synaptic current (Ch. 2).
- Eschbach, C. et al. (2021). “Recurrent architecture for adaptive regulation of learning in the insect brain.” *eLife* 10:e62567. [Article](https://elifesciences.org/articles/62567). Larval MBON-m1 calcium/learning observations do not measure KC→MBON-d1 unitary efficacy.
- Ohyama, T. et al. (2015). “A multilevel multimodal circuit enhances action selection in Drosophila.” *Nature* 520:633–639. [Article](https://www.nature.com/articles/nature14297). Supports Goro’s behavioral command-like role and separate VNC pathways; it does not provide the exact L2 edge transfer parameters.
- Hu, C. et al. (2023). “Cross-modal modulation gates nociceptive inputs in Drosophila.” *Current Biology*. [Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC10089977/). Larval VNC SON electrophysiology is adjacent evidence; the recorded cell classes are not the exact PN→Ipsigoro cells.
- Huber, A. et al. (2009). “Temporal Dynamics of Neuronal Activation by Channelrhodopsin-2 and TRPA1 Determine Behavioral Output in Drosophila Larvae.” *PLoS ONE* 4(10):e6955. [Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC2694103/). Quantitative electrophysiology is from larval motor neurons, not L2 brain pathway cells.
- Schlegel, P. et al. (2023). “The cellular architecture of memory modules in Drosophila supports stochastic input integration.” [Primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC10069864/). Absolute patch-clamp measurements are adult MBON-α3, not larval MBON-d1.

No model or run artifact was edited. No simulation or tuning was performed.

