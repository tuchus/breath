# Hardware notes

## Wiring

Everything is STEMMA QT, no soldering:

```
QT Py RP2040 ──100mm──▶ BMP585 (0x47) ──100mm──▶ AS5600 (0x36)
```

Order on the chain doesn't matter electrically. The two addresses don't
collide, and both boards have a connector on each side so they pass the bus
through. Check with `firmware/tools/i2c_scan.py`; you should see `0x36` and
`0x47`.

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

## AS5600 second axis

The AS5600 needs a **diametrically** magnetised disc magnet (6 mm is the
usual size) centred over the chip, 0.5 – 3 mm away, rotating in the plane of
the board. Ideas that pair well with breath:

- **Bite / lip lever** on the mouthpiece with a return spring, mapped to
  pitch or vibrato.
- **Thumb wheel** where your hand rests, mapped to CC 1 (mod) or CC 11
  (expression).

Set `ANGLE_MIN` / `ANGLE_MAX` in `code.py` to the `raw_angle` values at the
two ends of travel, read from `tools/monitor.py`.
