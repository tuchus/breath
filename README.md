# breath

A USB MIDI breath controller built from an Adafruit QT Py RP2040 and a
BMP585 pressure sensor, to play alongside the flywheel controller.

## Parts

| Qty | Part                                              | Role                         |
|-----|---------------------------------------------------|------------------------------|
| 1   | Adafruit QT Py RP2040 (4900)                      | USB MIDI device, runs firmware |
| 1   | Adafruit BMP585 ported pressure sensor (6413)     | Breath pressure              |
| 1   | STEMMA QT 100 mm cable (4210)                     | Connect the sensor           |

Plus: ~3 mm ID silicone tubing and a mouthpiece (a straw will do to start).

## Plan

1. **Wire and scan.** Plug the BMP585 into the QT Py. Flash CircuitPython,
   run `firmware/tools/i2c_scan.py`, confirm `0x47` appears.
2. **Read pressure.** Run `firmware/tools/monitor.py`, blow into the bare
   sensor port, watch the delta column move. Note gentle / normal / hard
   values.
3. **Build the air path.** Tube + bleed hole + mouthpiece. See
   `docs/hardware.md`. Re-run the monitor and re-note the values; the bleed
   hole changes them a lot.
4. **Send MIDI.** Copy `firmware/code.py`, `firmware/breath.py` and
   `firmware/boot.py` to the board, set `THRESHOLD_HPA` / `FULL_SCALE_HPA` from step 3, and check the
   "Breath Controller" device shows up in your DAW sending CC 2.
5. **Tune feel.** `CURVE`, `SMOOTHING`, and bleed hole size, in a loop with
   a breath-aware patch (a wind instrument or anything with CC 2 → volume /
   filter).
6. **Enclosure**, and if latency or jitter turns out to matter, port the
   loop to Arduino/C++ (Adafruit_BMP5xx + TinyUSB MIDI) on the same wiring.

## Firmware setup (CircuitPython)

The same firmware runs on the QT Py RP2040 or on a Raspberry Pi Pico /
Pico 2 W; only the wiring differs (see `docs/hardware.md`).

1. Install the latest CircuitPython UF2 for your board (hold BOOT / BOOTSEL,
   plug in, drop the `.uf2` onto `RPI-RP2`). Flashing CircuitPython replaces
   whatever firmware the board had, so keep a copy of the flywheel code if
   you borrow its Pico.
2. From the matching CircuitPython library bundle, copy to `CIRCUITPY/lib/`:
   - `adafruit_bmp5xx.mpy`
   - `adafruit_bus_device/` (folder)
   - `adafruit_register/` (folder)
   - `neopixel.mpy` (optional, QT Py only, onboard LED level meter)
3. Copy `firmware/code.py`, `firmware/breath.py` and `firmware/boot.py` to
   `CIRCUITPY/`. `boot.py` only takes effect after a power cycle.

`usb_midi` is built into CircuitPython, so no MIDI library is needed; the
firmware writes the 3-byte CC messages directly.

## MIDI output

| Message            | Source                       | Default |
|--------------------|------------------------------|---------|
| CC 2 (breath)      | BMP585 pressure above ambient| on, 7-bit; `SEND_14BIT` adds CC 34 |

Channel 1. All of this is in the `TUNING` block at the top of
`firmware/code.py`.

## Desktop tools

- **`tools/bench.html`**: open in Chrome or Edge. Shows CC 2 live from the
  controller over Web MIDI, and plots the pressure delta from the serial
  console over Web Serial, with peak and rest-noise readouts for picking
  `THRESHOLD_HPA` and `FULL_SCALE_HPA`. Can save a serial capture to a file.
- **`tools/simulate.py`**: replays a synthetic breath phrase (or a saved
  capture with `--trace`) through the mapping and prints an ASCII plot, so
  you can compare `--curve` and `--smoothing` settings without hardware.
- **`tests/`**: `python3 -m pytest` checks the mapping logic on the desktop.
  The mapping lives in `firmware/breath.py`, which has no board
  dependencies and runs unchanged under CircuitPython and CPython.

## Layout

```
firmware/code.py          main controller loop (sensor, MIDI, LED)
firmware/breath.py        pressure -> CC mapping, board-independent
firmware/boot.py          USB device name
firmware/tools/           i2c_scan.py, monitor.py (bring-up and tuning, run on the board)
tools/bench.html          browser MIDI meter + serial plotter
tools/simulate.py         desktop replay of the mapping
tests/test_breath.py      pytest suite for the mapping
docs/hardware.md          air path, moisture, bleed hole, wiring
```
