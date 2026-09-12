# Hardware notes

## Wiring

### QT Py RP2040

One STEMMA QT cable, no soldering:

```
QT Py RP2040 ──100mm──▶ BMP585 (0x47)
```

### Raspberry Pi Pico / Pico 2 W

The Pico has no STEMMA socket, so the four sensor lines go to header pins.
Either a STEMMA QT to male-jumper cable (Adafruit 4209), or cut one plug off
a STEMMA cable and use the bare wires, or solder to the breakout's
through-hole pads. Wire colours on STEMMA cables:

| Wire   | Signal | Pico pin (default in code)       |
|--------|--------|----------------------------------|
| black  | GND    | any GND (e.g. physical pin 38)   |
| red    | 3V     | 3V3 OUT (physical pin 36)        |
| blue   | SDA    | GP4 (physical pin 6)             |
| yellow | SCL    | GP5 (physical pin 7)             |

Any other I2C pair works too (GP6/GP7, GP8/GP9, ...); change `I2C_SDA` /
`I2C_SCL` at the top of `code.py` and the tools to match. The breakout has
its own pull-up resistors, so nothing else is needed.

Either way, check with `firmware/tools/i2c_scan.py`; you should see `0x47`.

## Air path

The BMP585 measures **absolute** pressure. The firmware takes a baseline at
boot and reports how far above ambient you're blowing, so the sensor just
needs to see the pressure inside the tube.

```
mouth ▶ mouthpiece ▶ tube ─┬─▶ bleed hole (to air)
                           └─▶ BMP585 port
```

Three things matter:

1. **Bleed hole.** Without one, the tube is a sealed bag: the pressure jumps
   when you seal your lips and doesn't fall until you open them, which feels
   like an on/off switch. A small leak (start around 1 mm, enlarge to taste)
   makes pressure track your effort continuously and lets you articulate
   notes with your tongue. Bigger hole = you have to blow harder for the same
   CC value, but response is faster and more natural.
2. **Moisture.** Breath is wet. Put the sensor *above* the tube so
   condensation drains away from it, keep the sensor in a short dead-end stub
   off the main tube (a T-piece), and let the main tube exit through the
   bleed hole so moisture has somewhere to go. A scrap of hydrophobic filter
   (a Gore vent, or the membrane from a syringe filter) in the stub is the
   belt-and-braces option.
3. **Tube fit.** The BMP585 ported board has a small barbed nub. Standard
   aquarium/CPAP-style silicone tubing with ~3 mm ID pushes on. If the ID is
   larger, use a short adapter or a drop of hot glue as a collar.

A cheap first mouthpiece: a plastic drinking straw or trimmed ballpoint pen
barrel, hot-glued into the tubing, with the bleed hole drilled in the tubing
just past the mouthpiece.

## Pressure ranges (rough)

| Action                     | Delta above ambient |
|----------------------------|---------------------|
| Sensor noise (4x OSR)      | < 0.02 hPa          |
| Gentle sustained blow      | 2 – 8 hPa           |
| Normal playing             | 8 – 25 hPa          |
| Hard blow                  | 30 – 60 hPa         |

These depend heavily on the bleed hole size. Measure your own with
`firmware/tools/monitor.py` before setting `THRESHOLD_HPA` and
`FULL_SCALE_HPA` in `code.py`.
