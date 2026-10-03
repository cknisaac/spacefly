# Playable osu!mania recreation — active plan

**Decision (2026-10-03):** Finish a playable osu!mania recreation for the
user's chosen maps, report the finished game and its known limits, and **stop**.
The user will decide when to circle back to the fly. Do not begin fly-policy
integration, learning, sensory encoding, reward design, or other research
experiments as part of this plan. Game-rule and playback checks against
osu!lazer are part of building the recreation. This priority supersedes
L0.12 as the next implementation step; L0.12 remains an unverified,
deferred policy-adapter proposal.

## Target and current position

- Initial target: native 4K osu!mania maps at normal rate with no mods. The
  user's maps are overwhelmingly taps, with roughly 2,000 tap notes per long
  note on many maps. This is a workload description, not a fixed note count or
  a special case in the implementation. Support any number of long notes
  present in a selected map without dropping or replacing them with taps.
- Current evidence after the generic build: the playable 4K client loads
  `.osu`/`.osz`, plays audio, accepts live input, renders and judges tap and
  hold notes, and reaches results. The pinned osu!lazer host matched the
  frozen tap corpus and six long-note traces. See the
  [build result](OSU_MANIA_RECREATION_RESULT.md).
- Current evidence for the first selected map: Freedom Dive 4K Normal loaded
  with audio; all 1,310 objects and an ideal full-song replay matched the
  pinned osu!lazer source host. See the
  [map-specific result](OSU_MANIA_FREEDOM_DIVE_NORMAL_RESULT.md).
- Current gap: physical audio latency and live manual play through the
  recreation remain unmeasured. The installed lazer binary is older than the
  pinned source test host, so exact binary-version replay parity was not run.
- Pin comparisons to osu!lazer `2026.1001.0-tachyon`, commit
  `da27300fcbfa246f87c3ba1a14cbd00b68c7e9a9`, unless a later explicit
  decision changes the reference.

## Build order

1. **Lock the real map corpus.** Obtain the target `.osu` file and associated
   audio/assets, plus a small set of other user-selected mostly tap maps.
   Inventory key count, timing points and scroll changes, note counts, long
   note start/end times, overlaps, hitsounds, and any unsupported features.
2. **Complete game rules.** Extend the deterministic four-lane engine to parse
   those maps and judge long-note heads, held state, releases/tails, breaks and
   represses, with matching combo, accuracy, and Score V2 behavior. Preserve
   the already verified tap cases and compare newly added cases with pinned
   osu!lazer. Implement long-note behavior as general game rules, regardless
   of how rare those objects are in the selected maps.
3. **Make it playable.** Add map selection, music playback tied to one game
   clock, lane/scroll rendering including long-note bodies, live key input,
   pause/restart, hitsounds where present, and an end-of-map result. The
   on-screen positions and judgement timing must use the same map timeline.
4. **Finish map-level conformance.** Play and replay each selected map from
   start to results. Check parsed objects against the source map; compare
   matched key-input traces, judgements, combo, accuracy, and score with the
   pinned runtime, including every long note in each selected map. Check
   audio/visual sync and live input by playing the client. Record any known
   differences instead of claiming general osu!mania parity from a small set.
5. **Deliver the recreation and stop.** Make the playable build and selected
   map instructions available, record the exact supported features and any
   remaining differences from the pinned runtime, and summarize the evidence
   that the completion criterion below is met. Stop at this checkpoint for
   user review. Do not start the deferred L0.12 adapter or another fly stage.

## Completion criterion for this target

The recreation is ready for the user's initial use when the selected 4K maps
load without silently losing objects, can be played with their music and long
notes from selection through results at rate 1 with no mods, and the matched
replay cases have no unexplained gameplay, judgement, combo, accuracy, or
score differences from the pinned osu!lazer reference. Document the exact
maps and covered features. Broader key counts, mods, rate changes, and
arbitrary-map compatibility can be separate extensions after this target.

**Scope guard:** Prioritize missing game behavior and a complete play session
over experimental adapters. Source checks, game-rule fixtures, and parity
probes may be used to verify the recreation. Do not introduce policy-specific
observations, experiment-only constraints, or fly-training work into this
build. Once the completion criterion is met, stop; any later fly work needs a
new user direction. The earlier biological teaching-rule no-go remains a
separate constraint on claims about fly learning, not a blocker for the game.
