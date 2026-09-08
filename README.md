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
4. **Send MIDI.** Copy `firmware/code.py` and `firmware/boot.py` to the
   board, set `THRESHOLD_HPA` / `FULL_SCALE_HPA` from step 3, and check the
   "Breath Controller" device shows up in your DAW sending CC 2.
5. **Tune feel.** `CURVE`, `SMOOTHING`, and bleed hole size, in a loop with
   a breath-aware patch (a wind instrument or anything with CC 2 → volume /
   filter).
6. **Enclosure**, and if latency or jitter turns out to matter, port the
   loop to Arduino/C++ (Adafruit_BMP5xx + TinyUSB MIDI) on the same wiring.

## Firmware setup (CircuitPython)

1. Install the latest CircuitPython UF2 for the QT Py RP2040 (hold BOOT,
   plug in, drop the `.uf2` onto `RPI-RP2`).
2. From the matching CircuitPython library bundle, copy to `CIRCUITPY/lib/`:
   - `adafruit_bmp5xx.mpy`
   - `adafruit_bus_device/` (folder)
   - `adafruit_register/` (folder)
   - `neopixel.mpy` (optional, for the onboard LED level meter)
3. Copy `firmware/code.py` and `firmware/boot.py` to `CIRCUITPY/`.
   `boot.py` only takes effect after a power cycle.

`usb_midi` is built into CircuitPython, so no MIDI library is needed; the
firmware writes the 3-byte CC messages directly.

## MIDI output

| Message            | Source                       | Default |
|--------------------|------------------------------|---------|
| CC 2 (breath)      | BMP585 pressure above ambient| on, 7-bit; `SEND_14BIT` adds CC 34 |

Channel 1. All of this is in the `TUNING` block at the top of
`firmware/code.py`.

## Layout

```
firmware/code.py          main controller loop
firmware/boot.py          USB device name
firmware/tools/           i2c_scan.py, monitor.py (bring-up and tuning)
docs/hardware.md          air path, moisture, bleed hole
```
