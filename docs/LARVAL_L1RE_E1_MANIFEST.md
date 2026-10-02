# L1R-E1 immutable manifest result

**Date:** 2026-10-02  
**Decision:** **PASS**  
**Variant:** L1R-E, selected by the user after literal L1R failed its learning-locus gate.

## Frozen scope

L1R-E retains the measured first-instar KC→MBON-m1 anatomy and tests an intentionally narrower model. The local teaching input is an **ENGINEERING ASSUMPTION** without a DAN identity. The inverse MBON-m1→action mapping is an **ENGINEERING OVERLAY**. Neither boundary is an anatomical edge.

The permitted claim, if every later gate passes, is limited to a connectome-constrained MBON-m1 model that stores an association in internal KC→MBON-m1 weights under an artificial local teacher and drives a fixed non-trainable action interface.

## Reproducible build

- Builder: `scripts/build_larval_l1re_manifest.py`
- Manifest: `configs/larval_l1re_manifest_v1.json`
- Manifest SHA-256: `58AAE08A16C9CAABB1A987B6FB10B4C81908722ABEEC60182ABF2483B7036A9C`
- Pinned S1 archive SHA-256: `8C1F43809ED5D527BA61B154E377CC21DA26383A75EDA8AAB85CE05607A72A4C`
- L1R-0 audit SHA-256: `1509A7B9FF6107517E9DD51BF4551B4A591239F65937DB81CAB8A3F16A934167`

Two complete builder runs produced the same manifest bytes and hash.

## Integrity checks

| Check | Result |
|---|---:|
| Unique nodes | 90 |
| Annotated KCs | 88 |
| Bilateral MBON-m1 cells | 2 |
| KC→MBON-m1 rows | 88 |
| KC→MBON-m1 contacts | 437 |
| Positive contact counts | PASS |
| Every endpoint present | PASS |
| Duplicate source pairs | 0 |
| Included-contact rationale coverage | 100% |
| DAN nodes or edges | 0 |
| Motor neurons | 0 |

The plastic mask includes all measured whole-cell KC→MBON-m1 rows. This is an **INFERRED** candidate mask because the source does not establish a compartment-specific plastic locus. No contact was excluded, so exclusion coverage is vacuous and explicit.

## Gate decision

L1R-E1 **PASS**. The measured anatomy is reproducible and the artificial teaching/action boundaries are explicit. This admits only the frozen electrical-family specification and pre-training controllability work; it does not admit a plasticity rule or establish learning.

