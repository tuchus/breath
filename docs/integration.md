# Integrating breath with the spinning wheel

Written 2026-09-12 against `tuchus/spinning-wheel-v2` at `1ab3d82` and this
repo. Line numbers are from that commit; expect drift.

## The one rule that makes this cheap

**Breath is CC 2 (and CC 34 for the LSB) arriving on any port the app has
open.** The app decodes it the same way whether it comes from:

- a separate USB MIDI device (the QT Py or a spare Pico running this repo's
  firmware), or
- the wheel's own Pico, once the BMP585 is wired to it and the breath loop is
  folded into `firmware/code.py` there.

So the app work happens once, first, and can be built and tested today with
no breath hardware at all (any knob on the MiniLab 3 mapped to CC 2 stands in
for the sensor). The hardware merge later is then a pure wiring-and-firmware
change with zero app change.

## Phase A: the app learns breath (first, no firmware change)

All in `app/Source`. Order matters: the reading first, then the places it
shows up, then the musical use.

### A1. `Wheel` gets a breath reading and a second port

`Wheel.h` / `Wheel.cpp`. The class already owns the robust open / retry /
ghost-port logic (`tryOpen`, `timerCallback`, the every-2-seconds reopen), so
the breath port belongs here, not in `Rack`'s AUX path (that one feeds the
keyboard collector and would turn breath into note traffic).

- Add `std::atomic<double> breath { 0 }` and `double breath() const`.
- Decode in `handleIncomingMidiMessage` (`Wheel.cpp:138` onward), before the
  V1 CC switch: CC 2 latches the MSB and publishes `breath = msb / 127.0`;
  CC 34, if it ever arrives, refines to `((msb << 7) | lsb) / 16383.0`.
  Publish on the MSB, not only the LSB, so a 7-bit-only sender works.
- Add a second `MidiInput` (`breathInput`) with its own match string
  (`setBreathPortMatch`, default `"Breath Controller"`, the name `boot.py`
  in this repo sets). Same open loop as `tryOpen`, same callback, same
  drop-and-reopen in `timerCallback`. Guard: never match the wheel's own
  port (skip names containing the wheel match), and never match
  `"loopMIDI"` / `"Flywheel Telemetry"` (the stale-port lesson in
  `docs/HANDOFF.md`).
- `live()` stays about the wheel. Add `breathLive()` (a breath message in
  the last 10 s on either port), so the surface can show it and the brain
  can fall back to "no breath" cleanly.
- Settings: `breathPort` next to `wheelPort` (`MainComponent.cpp:1553` and
  `:1790`). A `BREATH` button beside `AUX KEYS` in CONNECT (`:175`) using the
  same menu pattern: none / each available input.

### A2. The snapshot carries it

`Brain.h:178` `WheelSnapshot`: add `double breath = 0; bool breathLive =
false;`. `Rack.cpp:877` fills it from `wheel.breath()` / `wheel.breathLive()`.
The REPLAY and TEST DRIVE branches leave it at 0 (no pretend breath).

### A3. Sources: MATRIX and scene dials

- `Rack.h:117` `LinkSource`: append `Breath` **after** `Drag`, before `NUM`,
  so saved routes keep their indices. `Rack.cpp:659` names: add `"BREATH"`.
  `Rack.cpp:723` switch: `case LinkSource::Breath: v = w.breath; break;`.
- `SceneGL.h:56` dial source names: append `"BREATH"` at the end, and carry
  `breath` in `SceneFrame` alongside `torque, push, energy, drag` (see
  `docs/V10.md`, "Where it is exposed"). Wherever the frame is built from the
  snapshot, copy `w.breath`.
- Telemetry CSV: add a `breath` column next to `torque,energy,drag`.

### A4. The musical use, minimal and switchable

One control in STUDIO > MIDI: **BREATH: OFF / EXPRESSION / VELOCITY / BOTH**
(`controls.breathMode`, saved). Default OFF so nothing changes for a rig
without breath.

- **EXPRESSION**: in the block at `Rack.cpp:1125`, the VOICE lane's
  expression becomes `brain.expression() * (breathLive ? breath : 1.0)`, sent
  as CC 11 and applied through `voice.setLevelScale` exactly as ORGAN already
  does. This is the wind-instrument feel: the wheel picks the note, breath
  is the loudness. Works with every voice, built-in or VST3.
- **VELOCITY**: in the brain's note emission, scale note-on velocity by
  breath (floor at 0.1 so a note still sounds when you tongue it late).
  DRUMMER BY EFFORT can take breath as loudness with momentum still as
  complexity; leave that as a follow-up unless it falls out for free.
- **CC OUT** (`Rack.cpp:1112`): CC 2 currently carries **effort** to the
  plugins. Breath is CC 2 by MIDI convention, and a Pigments patch will
  expect breath on it. Decision for Ross: either move effort to CC 3 and put
  breath on CC 2, or leave effort and send breath on CC 11 only. I'd move
  effort; nothing shipped depends on it and CC 2 = effort was a placeholder
  name for "how hard you're working", which breath now literally is.

### A5. Checks

- `--smoke` after every surface change (the BREATH button, the STUDIO row).
- `render-check.ps1`: add a `breath-expression` case with a fixed breath of
  0.5 so the level-scale path is measured, not eyeballed.
- Bench without hardware: open the app, set the breath port to `Minilab3`,
  map a knob to CC 2, choose EXPRESSION, spin TEST SPIN and turn the knob.
  Note the AUX path also opens Minilab3 for notes; two opens of one WinMM
  port can fail, so this test may need the AUX port set to none first.

## Phase B: the sensor moves onto the wheel's Pico

Do this once Phase A plays well on the separate board, and once the wheel's
own connector work (screw-terminal carrier, ferrules) is done, since it adds
four more wires to the same carrier.

### B1. Wiring

The AS5047P owns SPI0 on GP16 to GP19. The old AS5600 path used GP0/GP1 for
I2C. Put the BMP585 on **GP4 (SDA) / GP5 (SCL)**, I2C0, so the AS5600
fallback stays possible on GP0/GP1. Power from 3V3 OUT (pin 36), never VBUS.
Four wires from a STEMMA QT to male-header cable (Adafruit 4209) into the
screw terminals: black GND, red 3V3, blue SDA, yellow SCL. The breakout has
its own pull-ups.

### B2. Files onto CIRCUITPY

- `breath.py` and `tuning.py` from this repo, unchanged (no board
  dependencies).
- `adafruit_bmp5xx.mpy` into `lib/` (add to `firmware/lib-manifest.txt`);
  `adafruit_register` and `adafruit_bus_device` are already there.

### B3. `firmware/code.py` in the wheel repo

Four small edits in `main()` (`code.py:4799` onward):

1. **Init, optional.** After the sensor retry loop, try to open the BMP585 on
   `busio.I2C(board.GP5, board.GP4, frequency=400_000)` with the same
   `configure_sensor` routine as this repo's `code.py` (the ODR self-check).
   On any exception log once and set `bmp = None`: the wheel must never boot
   dead because the breath sensor is unplugged.
2. **Baseline.** One second of ambient averaging, same as here, into a
   `BreathMapper`. One second at boot is already spent on sensor retries and
   the watchdog is 2 s, so feed the watchdog during the average.
3. **Loop.** Once per iteration, next to the V2 frame send: `if bmp and
   bmp.data_ready:` read pressure, `mapper.update()`, and on change
   `midi.send(ControlChange(2, mapper.msb))`. One 3-byte I2C read at 400 kHz
   is well under 0.2 ms; the loop runs on a 5 ms frame, so this costs nothing
   measurable. The change-gating means at rest it sends nothing.
4. **Tuning input.** The wheel's `adafruit_midi.MIDI(...)` is built with
   `in_channel=0` (`code.py:5040`), which silently drops channel 16. Change to
   `in_channel=(0, 15)` and, in the receive handler, route
   `msg.channel == 15` control changes to `tuning.apply(mapper, ...)`, which
   also answers `rezero` and `report`. The tuning CCs are 40 to 45; the
   wheel's own control CCs are 20 and 81 to 122, so there's no overlap even
   if the channel guard is ever lost.

The V2 SysEx frame stays at version 2. Breath doesn't need to be atomic with
the angle; 7-bit CC at up to 140 Hz is more than the synth can use. If it
ever matters (a recorded ride replaying breath in lockstep with angle), a
version-3 frame adds two bytes and the app's decoder grows one branch.

### B4. App change for Phase B

None. CC 2 now arrives on the wheel port; `Wheel::handleIncomingMidiMessage`
already decodes it from A1. Set the breath port to none in CONNECT so the app
stops looking for a second device.

## Phase C: once it's felt

Ideas in rough order of payoff, none of them needed to start:

- **Breath gates the ENGINES lane.** Rhythm stops when you stop blowing, like
  a saxophonist's band. One multiply in the ENGINES lane's level.
- **Breath in the DRUMMER pad.** Breath is loudness, momentum is busyness.
- **A BREATH scene dial default** on a couple of scenes (GLOW on TRIP, the
  bloom on COLOR POUR), so the picture breathes.
- **Ride files.** When CAPTURE and REC merge (V10 idea 4), breath is one more
  column to record and replay.
- **Bite or tilt** as a second axis, if the mouthpiece grows a lever. The
  AS5600 that came out of this repo would do it, and its driver is already
  in the wheel's lib folder.

## Decisions for Ross before Phase A starts

1. CC OUT: move effort to CC 3 so breath can be CC 2, or keep effort and send
   breath on CC 11 only?
2. Default musical role: EXPRESSION only (my pick), or VELOCITY too?
3. Where the sensor lives long-term: separate board (two USB cables, no
   changes to the carrier) or merged (one cable, four more terminals).
   The plan above works either way, in that order.
