# Tuning guide

Four numbers decide how the controller feels. All live in the TUNING block
at the top of `firmware/code.py`, and all can be changed live from the
sliders in `tools/bench.html` while you play, then pasted back into the
file once they're right.

| Constant         | What it is                                              | Default |
|------------------|---------------------------------------------------------|---------|
| `THRESHOLD_HPA`  | Pressure above ambient before CC 2 leaves zero          | 0.5     |
| `FULL_SCALE_HPA` | Pressure above ambient that gives CC 2 = 127            | 25      |
| `CURVE`          | Shape between those two points (1 = straight line)      | 0.7     |
| `SMOOTHING`      | How much of each new sample is used (1 = none)          | 0.35    |

## How to pick them

1. Run the monitor (or `code.py` with `DEBUG = True`) with the bench page's
   serial panel connected.
2. **Sit still, don't blow.** The "rest noise" readout is the peak-to-peak
   wobble at rest. Set `THRESHOLD_HPA` to roughly three times that. With the
   sensor's own filter on, it's usually well under 0.1 hPa, so 0.3 to 0.5 is
   typical.
3. **Blow as hard as you would ever play.** Not as hard as you can; as hard
   as a fortissimo. Set `FULL_SCALE_HPA` a little under that peak so you can
   actually reach 127.
4. Leave `CURVE` and `SMOOTHING` at the defaults, load `code.py`, and play a
   patch for ten minutes before touching them.

## Symptoms

- **Notes start late or need a puff to begin.** Threshold too high. Lower it
  until it's just above the rest noise.
- **CC 2 flickers between 0 and 1 at rest.** Threshold too low, or the
  baseline drifted. Raise the threshold a little, or press Re-zero on the
  bench page. If it drifts within minutes, check the tube for a slow leak
  around the sensor nozzle.
- **Can't reach 127, or only with a huge blow.** Full scale too high, or the
  bleed hole is too big so pressure never builds. Lower full scale first;
  if you then hit 127 at a comfortable level but quiet playing is cramped
  into a few CC steps, the bleed hole is the real culprit. Tape over half
  of it and re-measure.
- **Everything happens in the first bit of breath, then it's flat.** Full
  scale too low, or the bleed hole too small so pressure spikes instantly.
- **Quiet playing has no detail.** Lower `CURVE` (0.5 to 0.7) to stretch the
  bottom of the range.
- **Hard to hold a steady loud note; it jumps to max too easily.** Raise
  `CURVE` toward 1.0 or a little above.
- **Response feels laggy or rubbery.** Raise `SMOOTHING` (more of each new
  sample). Also try the sensor's IIR coefficient in `configure_sensor`: it's
  set to 3; 1 or bypass is snappier.
- **Output is jittery, the synth sounds grainy on sustained notes.** Lower
  `SMOOTHING`, or raise the sensor IIR coefficient to 7. If that makes it
  laggy, the noise is probably mechanical: a loose tube, or the tube
  resting on something that vibrates.
- **Feels like an on/off switch.** The bleed hole is too small or missing.
  Enlarge it until a gentle sustained blow gives a stable mid value.
- **Articulation is mushy; tonguing doesn't cut the note.** Bleed hole too
  small (pressure can't fall fast enough) or smoothing too low a value
  (too much averaging). Enlarge the hole first.

## Baseline drift

Ambient pressure moves with weather, doors opening, and air conditioning.
The firmware re-measures ambient for a second at boot, then follows slow
drift at `BASELINE_TRACK` per sample only while the pressure is below the
threshold, so blowing never pulls the baseline up. If you change rooms or
the value creeps, press Re-zero on the bench page or power-cycle.

## 14-bit output

`SEND_14BIT = True` sends CC 2 plus CC 34 for 16384 steps instead of 128.
Only useful if your synth reads the LSB; most don't, and the extra messages
double the MIDI traffic. Leave it off unless you hear stepping on slow swells.
